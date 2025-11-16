"""Simulate a season schedule using the play-balance engine.

This script loads real rosters and plays out an entire schedule generated for
the configured teams.  Box score totals are aggregated across the league and
compared to MLB benchmarks.

Usage examples::

    python scripts/playbalance_simulate.py --seed 1
    python scripts/playbalance_simulate.py --games 20 --output results.json
    python scripts/playbalance_simulate.py --perftune

Enable PerfTune profiling with ``--perftune`` and analyze the results with
``perftune view`` after the simulation completes.

"""

from __future__ import annotations

import argparse
import copy
import json
import multiprocessing as mp
import os
import pickle
import random
import sys
from contextlib import nullcontext
from datetime import date
from pathlib import Path

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover - fallback when tqdm unavailable
    def tqdm(iterable, **kwargs):
        return iterable

# Allow running the script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playbalance.benchmarks import load_benchmarks, league_average
from playbalance.schedule_generator import generate_mlb_schedule
from playbalance.sim_config import load_tuned_playbalance_config
from playbalance.simulation import FieldingState, GameSimulation, PitcherState, TeamState
from playbalance.batter_ai import (
    reset_swing_diagnostics,
    swing_diagnostics_summary,
    auto_take_summary,
    SWING_PITCH_DIAGNOSTICS,
    SWING_COUNT_DIAGNOSTICS,
    AUTO_TAKE_DIAGNOSTICS,
)
from utils.lineup_loader import build_default_game_state
from utils.team_loader import load_teams

try:  # pragma: no cover - optional dependency
    import numpy as np
except ImportError:  # pragma: no cover - fallback when numpy unavailable
    np = None


if np is None:  # pragma: no cover - numpy is required for this script
    raise RuntimeError("NumPy is required to run this script")


def configure_perf_tuning() -> None:
    """Configure process priority and CPU affinity using ``psutil``."""

    try:
        import psutil
    except ImportError:
        print("[PerfTune] psutil not installed; skipping priority/affinity tuning")
        return

    p = psutil.Process()

    try:
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        print("[PerfTune] Process priority set to High")
    except Exception as e:  # pragma: no cover - platform dependent
        print(f"[PerfTune] Could not set priority: {e}")

    try:
        cpu_count = os.cpu_count() or 1
        p.cpu_affinity(list(range(cpu_count)))
        print(f"[PerfTune] CPU affinity set to all {cpu_count} cores")
    except Exception as e:  # pragma: no cover - platform dependent
        print(f"[PerfTune] Could not set CPU affinity: {e}")


# STAT_KEYS defines the column order for all stat arrays produced by
# ``_simulate_game``.  The first 19 entries correspond to batting statistics.
# The remaining seven indices capture pitching metrics.  Contributors adding
# new stats should append to this list and update the extraction logic
# accordingly.
STAT_KEYS = [
    "pa",
    "bb",
    "k",
    "h",
    "hr",
    "ab",
    "r",
    "sf",
    "sb",
    "cs",
    "hbp",
    "b1",
    "b2",
    "b3",
    "gb",
    "ld",
    "fb",
    "roe",
    "gidp",
    "pitches_thrown",
    "zone_pitches",
    "zone_swings",
    "zone_contacts",
    "o_zone_swings",
    "o_zone_contacts",
    "so_looking",
]

STAT_INDEX = {k: i for i, k in enumerate(STAT_KEYS)}


BASE_STATES: dict[str, TeamState] = {}
CFG = None


class FastRNG:
    """Adapter providing a ``random.Random``-like API."""

    def __init__(self, seed: int | None = None) -> None:
        if np is not None:
            self._rng = np.random.default_rng(seed)
            self._numpy = True
        else:  # pragma: no cover - fallback to stdlib RNG
            self._rng = random.Random(seed)
            self._numpy = False

    def random(self) -> float:
        return float(self._rng.random())

    def uniform(self, a: float, b: float) -> float:
        if self._numpy:
            return float(self._rng.uniform(a, b))
        return self._rng.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        if self._numpy:
            return int(self._rng.integers(a, b + 1))
        return self._rng.randint(a, b)

    def shuffle(self, x) -> None:  # pragma: no cover - simple passthrough
        self._rng.shuffle(x)


def _init_worker(states: dict[str, bytes], cfg) -> None:
    global BASE_STATES, CFG
    BASE_STATES = {
        team_id: pickle.loads(state) for team_id, state in states.items()
    }
    CFG = cfg


def clone_team_state(team_id: str) -> TeamState:
    """Return a fresh ``TeamState`` cloned from the baseline."""

    return copy.deepcopy(BASE_STATES[team_id])


def _simulate_game(args: tuple[str, str, int]) -> np.ndarray:
    """Simulate a single game and return leaguewide stat totals.

    The returned array has one entry per ``STAT_KEYS`` element.  Rows for
    individual players follow the same layout so they can be summed
    consistently.  Batting stats occupy indices 0-18, while pitching metrics
    use 19-25.
    """

    home_id, away_id, seed = args
    home = clone_team_state(home_id)
    away = clone_team_state(away_id)
    sim = GameSimulation(home, away, CFG, FastRNG(seed))
    sim.simulate_game(persist_stats=False)

    totals = np.zeros(len(STAT_KEYS), dtype=np.int64)

    for team in (home, away):
        # Gather per-batter stats into a 2D array and accumulate.
        batter_count = len(team.lineup_stats)
        if batter_count:
            batter_iter = (
                stat
                for bs in team.lineup_stats.values()
                for stat in (
                    bs.pa,
                    bs.bb,
                    bs.so,
                    bs.h,
                    bs.hr,
                    bs.ab,
                    bs.r,
                    bs.sf,
                    bs.sb,
                    bs.cs,
                    bs.hbp,
                    bs.b1,
                    bs.b2,
                    bs.b3,
                    bs.gb,
                    bs.ld,
                    bs.fb,
                    bs.roe,
                    bs.gidp,
                )
            )
            batter_stats = np.fromiter(
                batter_iter, dtype=np.int64, count=batter_count * 19
            ).reshape(batter_count, 19)
            np.add(
                totals[:19],
                batter_stats.sum(axis=0, dtype=np.int64),
                out=totals[:19],
            )

        # Gather per-pitcher stats into a 2D array and accumulate.
        pitcher_count = len(team.pitcher_stats)
        if pitcher_count:
            pitcher_iter = (
                stat
                for ps in team.pitcher_stats.values()
                for stat in (
                    ps.pitches_thrown,
                    ps.zone_pitches,
                    ps.zone_swings,
                    ps.zone_contacts,
                    ps.o_zone_swings,
                    ps.o_zone_contacts,
                    ps.so_looking,
                )
            )
            pitcher_stats = np.fromiter(
                pitcher_iter, dtype=np.int64, count=pitcher_count * 7
            ).reshape(pitcher_count, 7)
            np.add(
                totals[19:],
                pitcher_stats.sum(axis=0, dtype=np.int64),
                out=totals[19:],
            )

    return totals


def _print_config_snapshot(cfg) -> None:
    """Print high-impact configuration values for tuning."""

    keys = [
        "swingProbScale",
        "zSwingProbScale",
        "oSwingProbScale",
        "contactFactorBase",
        "contactFactorDiv",
        "idRatingEaseScale",
        "missChanceScale",
        "twoStrikeContactFloor",
        "twoStrikeContactQuality",
        "twoStrikeContactBonus",
        "twoStrikeSwingBonus",
        "twoStrikeChaseBonusScale",
        "ballInPlayPitchPct",
        "targetPitchesPerPA",
        "autoTakeDistanceBase",
        "autoTakeDistanceBallStep",
        "autoTakeDistanceBuffer",
        "autoTakeDefaultChaseChance",
    ]
    values_dict = getattr(cfg, "values", {}) or {}
    print("\n[Config] Key tuning values:")
    for key in keys:
        value = getattr(cfg, key, None)
        raw = values_dict.get(key)
        if raw is not None and raw != value:
            print(f"  {key}: {value} (override {raw})")
        else:
            print(f"  {key}: {value}")


def _dump_swing_diagnostics(path: Path) -> None:
    """Persist raw swing/auto-take diagnostics as JSON."""

    data: dict[str, list[dict[str, float | int | str]]] = {
        "swing_pitch": [],
        "swing_count": [],
        "auto_take": [],
    }
    for (pitch_kind, balls, strikes), stats in SWING_PITCH_DIAGNOSTICS.items():
        entry: dict[str, float | int | str] = {
            "pitch_kind": pitch_kind,
            "balls": balls,
            "strikes": strikes,
        }
        entry.update(stats)
        data["swing_pitch"].append(entry)
    for (balls, strikes), stats in SWING_COUNT_DIAGNOSTICS.items():
        entry = {"balls": balls, "strikes": strikes}
        entry.update(stats)
        data["swing_count"].append(entry)
    for (balls, strikes), stats in AUTO_TAKE_DIAGNOSTICS.items():
        entry = {"balls": balls, "strikes": strikes}
        entry.update(stats)
        data["auto_take"].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"Saved swing diagnostics to {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Simulate games using the play-balance engine"
    )
    parser.add_argument(
        "--games",
        type=int,
        default=162,
        help="number of games each team plays",
    )
    parser.add_argument(
        "--start-date",
        type=lambda s: date.fromisoformat(s),
        default=date(2025, 4, 1),
        help="start date for the generated schedule (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="random seed for reproducibility",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional file to write JSON aggregated results to",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="disable progress bar",
    )
    parser.add_argument(
        "--perftune",
        action="store_true",
        help="enable PerfTune profiling",
    )
    parser.add_argument(
        "--disable-calibration",
        action="store_true",
        help="disable pitch calibration and target pitches/PA adjustments",
    )
    parser.add_argument(
        "--pitch-calibration",
        action="store_true",
        help="enable pitch calibration targeting realistic pitches per PA",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="print key configuration values before running games",
    )
    parser.add_argument(
        "--diag-output",
        type=Path,
        default=None,
        help="optional path to write raw swing/auto-take diagnostics (JSON)",
    )
    args = parser.parse_args(argv)

    configure_perf_tuning()

    benchmarks = load_benchmarks()
    cfg, mlb_averages = load_tuned_playbalance_config(apply_benchmarks=True)
    if args.pitch_calibration and os.getenv("PB_ENABLE_CALIBRATION") != "1":
        target_source = mlb_averages.get("pitches_per_pa") or getattr(cfg, "pitchCalibrationTarget", 3.9)
        try:
            target_value = round(float(target_source) - 0.31, 2)
        except (TypeError, ValueError):
            target_value = 3.8
        cfg.pitchCalibrationEnabled = 1
        cfg.pitchCalibrationTarget = max(0.0, target_value)
        cfg.pitchCalibrationTolerance = 0.05
        cfg.pitchCalibrationPerPlateCap = 2
        cfg.pitchCalibrationPerGameCap = 0
        cfg.pitchCalibrationMinPA = max(6, int(getattr(cfg, "pitchCalibrationMinPA", 6) or 6))
        cfg.pitchCalibrationPreferFoul = 1
        cfg.pitchCalibrationEmaAlpha = 0.3
        if hasattr(cfg, "values"):
            cfg.values.update(
                {
                    "pitchCalibrationEnabled": 1,
                    "pitchCalibrationTarget": cfg.pitchCalibrationTarget,
                    "pitchCalibrationTolerance": cfg.pitchCalibrationTolerance,
                    "pitchCalibrationPerPlateCap": cfg.pitchCalibrationPerPlateCap,
                    "pitchCalibrationPerGameCap": cfg.pitchCalibrationPerGameCap,
                    "pitchCalibrationMinPA": cfg.pitchCalibrationMinPA,
                    "pitchCalibrationPreferFoul": cfg.pitchCalibrationPreferFoul,
                    "pitchCalibrationEmaAlpha": cfg.pitchCalibrationEmaAlpha,
                }
            )
    elif args.disable_calibration:
        if hasattr(cfg, "pitchCalibrationEnabled"):
            cfg.pitchCalibrationEnabled = 0
        if hasattr(cfg, "values"):
            cfg.values["pitchCalibrationEnabled"] = 0
        if hasattr(cfg, "targetPitchesPerPA"):
            cfg.targetPitchesPerPA = 0
        if hasattr(cfg, "values"):
            cfg.values["targetPitchesPerPA"] = 0
    cfg.collectSwingDiagnostics = 1 if os.getenv("SWING_DIAGNOSTICS") else getattr(cfg, "collectSwingDiagnostics", 0)
    if hasattr(cfg, "values"):
        cfg.values["collectSwingDiagnostics"] = cfg.collectSwingDiagnostics
    if args.print_config:
        _print_config_snapshot(cfg)
    if getattr(cfg, "collectSwingDiagnostics", 0):
        reset_swing_diagnostics()

    team_ids = [t.team_id for t in load_teams("data/teams.csv")]
    base_states = {tid: pickle.dumps(build_default_game_state(tid)) for tid in team_ids}
    schedule = generate_mlb_schedule(team_ids, args.start_date, args.games)

    rng = np.random.default_rng(args.seed)
    seeds = rng.integers(
        0, np.iinfo(np.int32).max, size=len(schedule), dtype=np.int32
    )
    jobs = [(g["home"], g["away"], s) for g, s in zip(schedule, seeds)]

    chunksize = max(1, len(jobs) // (mp.cpu_count() * 4))
    totals_array = np.zeros(len(STAT_KEYS), dtype=np.int64)
    sequential = bool(args.diag_output and getattr(cfg, "collectSwingDiagnostics", 0))

    if args.perftune:
        try:  # pragma: no cover - optional dependency
            import perftune
        except ImportError as exc:  # pragma: no cover - missing perftune
            raise RuntimeError("--perftune requires the perftune package") from exc
        profile_ctx = perftune.tune()
    else:
        profile_ctx = nullcontext()

    with profile_ctx:
        if sequential:
            _init_worker(base_states, cfg)
            iterable = jobs
            if not args.no_progress:
                iterable = tqdm(
                    jobs,
                    total=len(jobs),
                    desc="Simulating games",
                    disable=False,
                )
            for job in iterable:
                totals_array += _simulate_game(job)
        else:
            with mp.Pool(initializer=_init_worker, initargs=(base_states, cfg)) as pool:
                for stats in tqdm(
                    pool.imap_unordered(_simulate_game, jobs, chunksize=chunksize),
                    total=len(jobs),
                    desc="Simulating games",
                    disable=args.no_progress,
                ):
                    totals_array += stats

    totals = {k: int(totals_array[i]) for i, k in enumerate(STAT_KEYS)}

    pa = totals["pa"] or 1
    pitches = totals["pitches_thrown"] or 1
    bip = totals["gb"] + totals["ld"] + totals["fb"]

    k_pct = totals["k"] / pa
    bb_pct = totals["bb"] / pa
    pitches_per_pa = pitches / pa
    pitches_put_in_play_pct = bip / pitches if pitches else 0.0
    bip_gb_pct = totals["gb"] / bip if bip else 0.0
    bip_fb_pct = totals["fb"] / bip if bip else 0.0
    bip_ld_pct = totals["ld"] / bip if bip else 0.0
    bip_double_play_pct = totals["gidp"] / bip if bip else 0.0
    hits_on_bip = totals["h"] - totals["hr"]
    babip = hits_on_bip / bip if bip else 0.0
    tb = (
        totals["b1"] + 2 * totals["b2"] + 3 * totals["b3"] + 4 * totals["hr"]
    )
    avg = totals["h"] / totals["ab"] if totals["ab"] else 0.0
    obp_den = totals["ab"] + totals["bb"] + totals["hbp"] + totals["sf"]
    obp = (
        (totals["h"] + totals["bb"] + totals["hbp"])
        / obp_den
        if obp_den
        else 0.0
    )
    slg = tb / totals["ab"] if totals["ab"] else 0.0
    iso = slg - avg
    swings = totals["zone_swings"] + totals["o_zone_swings"]
    contacts = totals["zone_contacts"] + totals["o_zone_contacts"]
    swstr_pct = (swings - contacts) / pitches if pitches else 0.0
    called_third_strike_share_of_so = (
        totals["so_looking"] / totals["k"] if totals["k"] else 0.0
    )
    o_zone_pitches = pitches - totals["zone_pitches"]
    o_swing_pct = (
        totals["o_zone_swings"] / o_zone_pitches if o_zone_pitches else 0.0
    )
    z_swing_pct = (
        totals["zone_swings"] / totals["zone_pitches"]
        if totals["zone_pitches"]
        else 0.0
    )
    swing_pct = swings / pitches if pitches else 0.0
    z_contact_pct = (
        totals["zone_contacts"] / totals["zone_swings"]
        if totals["zone_swings"]
        else 0.0
    )
    o_contact_pct = (
        totals["o_zone_contacts"] / totals["o_zone_swings"]
        if totals["o_zone_swings"]
        else 0.0
    )
    contact_pct = contacts / swings if swings else 0.0
    sb_attempts = totals["sb"] + totals["cs"]
    sba_rate = sb_attempts / pa
    sb_pct = totals["sb"] / sb_attempts if sb_attempts else 0.0
    total_runs = totals["r"]
    games_played = len(schedule)
    team_games = games_played * 2
    runs_per_team_game = total_runs / team_games if team_games else 0.0
    runs_allowed_per_team_game = runs_per_team_game
    der_den = pa - totals["bb"] - totals["k"] - totals["hbp"] - totals["hr"]
    defensive_efficiency = (
        1 - (totals["h"] + totals["roe"]) / der_den if der_den else 0.0
    )

    metrics = {
        "runs_per_team_game": runs_per_team_game,
        "runs_allowed_per_team_game": runs_allowed_per_team_game,
        "k_pct": k_pct,
        "bb_pct": bb_pct,
        "iso": iso,
        "babip": babip,
        "bip_gb_pct": bip_gb_pct,
        "bip_fb_pct": bip_fb_pct,
        "bip_ld_pct": bip_ld_pct,
        "pitches_per_pa": pitches_per_pa,
        "pitches_put_in_play_pct": pitches_put_in_play_pct,
        "sb_attempts_per_pa": sba_rate,
        "sb_pct": sb_pct,
        "defensive_efficiency": defensive_efficiency,
        "avg": avg,
        "obp": obp,
        "slg": slg,
        "bip_double_play_pct": bip_double_play_pct,
        "swstr_pct": swstr_pct,
        "called_third_strike_share_of_so": called_third_strike_share_of_so,
        "o_swing_pct": o_swing_pct,
        "z_swing_pct": z_swing_pct,
        "swing_pct": swing_pct,
        "z_contact_pct": z_contact_pct,
        "o_contact_pct": o_contact_pct,
        "contact_pct": contact_pct,
    }

    benchmark_keys = {
        "runs_per_team_game": None,
        "runs_allowed_per_team_game": None,
        "k_pct": "k_pct",
        "bb_pct": "bb_pct",
        "iso": "iso",
        "babip": "babip",
        "bip_gb_pct": "bip_gb_pct",
        "bip_fb_pct": "bip_fb_pct",
        "bip_ld_pct": "bip_ld_pct",
        "pitches_per_pa": "pitches_per_pa",
        "pitches_put_in_play_pct": "pitches_put_in_play_pct",
        "sb_attempts_per_pa": "sba_per_pa",
        "sb_pct": "sb_pct",
        "defensive_efficiency": "defensive_efficiency",
        "avg": "avg",
        "obp": "obp",
        "slg": "slg",
        "bip_double_play_pct": "bip_double_play_pct",
        "swstr_pct": "swstr_pct",
        "called_third_strike_share_of_so": "called_third_strike_share_of_so",
        "o_swing_pct": "o_swing_pct",
        "z_swing_pct": "z_swing_pct",
        "swing_pct": "swing_pct",
        "z_contact_pct": "z_contact_pct",
        "o_contact_pct": "o_contact_pct",
        "contact_pct": "contact_pct",
    }
    benchmark_values = {
        metric: (
            league_average(benchmarks, key, default=None) if key else None
        )
        for metric, key in benchmark_keys.items()
    }

    results = {
        "pa": totals["pa"],
        "k": totals["k"],
        "bb": totals["bb"],
        "hits": totals["h"],
        "home_runs": totals["hr"],
        "sb_success": totals["sb"],
        "sb_caught": totals["cs"],
    }
    results["metrics"] = metrics
    results["benchmarks"] = benchmark_values

    if args.output is not None:
        args.output.write_text(json.dumps(results, indent=2))
        print(f"Saved results to {args.output}")

    print(
        f"Pitches/PA: {pitches_per_pa:.2f} "
        f"(MLB {league_average(benchmarks, 'pitches_per_pa'):.2f})"
    )
    print(
        "Pitches Put In Play%: "
        f"{pitches_put_in_play_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'pitches_put_in_play_pct'):.3f})"
    )
    print(
        f"BIP GB%: {bip_gb_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_gb_pct'):.3f})"
    )
    print(
        f"BIP FB%: {bip_fb_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_fb_pct'):.3f})"
    )
    print(
        f"BIP LD%: {bip_ld_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_ld_pct'):.3f})"
    )
    print(
        f"Double Play%: {bip_double_play_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_double_play_pct'):.3f})"
    )
    print(f"AVG:  {avg:.3f} (MLB {league_average(benchmarks, 'avg'):.3f})")
    print(f"OBP:  {obp:.3f} (MLB {league_average(benchmarks, 'obp'):.3f})")
    print(f"SLG:  {slg:.3f} (MLB {league_average(benchmarks, 'slg'):.3f})")
    print(
        f"SwStr%: {swstr_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'swstr_pct'):.3f})"
    )
    called_share_avg = league_average(
        benchmarks, "called_third_strike_share_of_so"
    )
    print(
        "Called Strike 3 Share: "
        f"{called_third_strike_share_of_so:.3f} (MLB {called_share_avg:.3f})"
    )
    print(
        f"O-Swing%: {o_swing_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'o_swing_pct'):.3f})"
    )
    print(
        f"Z-Swing%: {z_swing_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'z_swing_pct'):.3f})"
    )
    print(
        f"Swing%: {swing_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'swing_pct'):.3f})"
    )
    print(
        f"Z-Contact%: {z_contact_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'z_contact_pct'):.3f})"
    )
    print(
        f"O-Contact%: {o_contact_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'o_contact_pct'):.3f})"
    )
    print(
        f"Contact%: {contact_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'contact_pct'):.3f})"
    )
    print(
        f"K%:  {k_pct:.3f} (MLB {league_average(benchmarks, 'k_pct'):.3f})"
    )
    print(
        f"BB%: {bb_pct:.3f} (MLB {league_average(benchmarks, 'bb_pct'):.3f})"
    )
    print(
        f"BABIP: {babip:.3f} (MLB {league_average(benchmarks, 'babip'):.3f})"
    )
    print(
        f"SB Attempt/PA: {sba_rate:.3f} "
        f"(MLB {league_average(benchmarks, 'sba_per_pa'):.3f})"
    )
    print(
        f"SB%: {sb_pct:.3f} (MLB {league_average(benchmarks, 'sb_pct'):.3f})"
    )

    if getattr(cfg, "collectSwingDiagnostics", 0):
        swing_lines = list(swing_diagnostics_summary(limit=10))
        if swing_lines:
            print("\nSwing diagnostics (top by samples):")
            for line in swing_lines:
                print(f"  {line}")
        auto_lines = list(auto_take_summary())
        if auto_lines:
            print("Auto-take diagnostics:")
            for line in auto_lines:
                print(f"  {line}")
        if args.diag_output is not None:
            _dump_swing_diagnostics(args.diag_output)

    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())

