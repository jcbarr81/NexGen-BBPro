"""Simulate a full 162-game season and report average box score stats.

The schedule should contain ``len(teams) * games_per_team // 2`` games; a
length mismatch likely means duplicate entries that would inflate averages.

For lengthy runs this script can benefit from PyPy's JIT or by invoking
CPython with ``python -O`` to skip asserts. When using PyPy ensure required
C extensions such as ``bcrypt`` are available; GUI-focused modules like
``PyQt6`` are not needed here.
"""




from __future__ import annotations
import os


def configure_perf_tuning() -> None:
    """Configure process priority and CPU affinity using ``psutil``.

    This function is intended to run only in the main process to avoid
    repeating the tuning in worker processes spawned by
    ``multiprocessing``.
    """

    try:
        import psutil
    except ImportError:
        print("[PerfTune] psutil not installed; skipping priority/affinity tuning")
        return

    p = psutil.Process()

    # --- Set priority ---
    try:
        # Default: High priority
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        # Alternatives:
        # p.nice(psutil.REALTIME_PRIORITY_CLASS)   # DANGEROUS: may freeze system
        # p.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        print("[PerfTune] Process priority set to High")
    except Exception as e:  # pragma: no cover - platform dependent
        print(f"[PerfTune] Could not set priority: {e}")

    # --- Set CPU affinity (all logical CPUs) ---
    try:
        cpu_count = os.cpu_count() or 1
        p.cpu_affinity(list(range(cpu_count)))
        print(f"[PerfTune] CPU affinity set to all {cpu_count} cores")
    except Exception as e:  # pragma: no cover - platform dependent
        print(f"[PerfTune] Could not set CPU affinity: {e}")

# --- Threading environment (vectorized libs like numpy, MKL, OpenMP) ---

from collections import Counter
from datetime import date
from pathlib import Path
import argparse
import csv
import pickle
import random
import sys
import multiprocessing as mp


cpu_count = os.cpu_count() or 1
os.environ.setdefault("OMP_NUM_THREADS", str(cpu_count))
os.environ.setdefault("MKL_NUM_THREADS", str(cpu_count))
os.environ.setdefault("NUMEXPR_MAX_THREADS", str(cpu_count))
os.environ.setdefault("NUMEXPR_NUM_THREADS", str(cpu_count))
os.environ.setdefault("KMP_AFFINITY", "granularity=fine,compact,1,0")
os.environ.setdefault("OMP_PROC_BIND", "true")

print(f"[PerfTune] Threading env set for {cpu_count} cores")
# -----------------------------------------------------------------------

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover
    def tqdm(iterable, **kwargs):
        return iterable

# Ensure project root is on the path when running this script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from logic.schedule_generator import generate_mlb_schedule
from logic.simulation import (
    GameSimulation,
    TeamState,
    generate_boxscore,
)
from logic.playbalance_config import PlayBalanceConfig
from logic.sim_config import apply_league_benchmarks
from utils.lineup_loader import build_default_game_state
from utils.path_utils import get_base_dir
from utils.team_loader import load_teams
import logic.simulation as sim


def _no_save_stats(players, teams):
    """No-op ``save_stats`` to avoid file I/O during benchmarking."""

    return None


sim.save_stats = _no_save_stats


STAT_ORDER = [
    "Runs",
    "Hits",
    "Doubles",
    "Triples",
    "HomeRuns",
    "Walks",
    "Strikeouts",
    "StolenBases",
    "CaughtStealing",
    "HitByPitch",
    "TotalPitchesThrown",
    "Strikes",
]


def clone_team_state(base: TeamState) -> TeamState:
    """Return a new ``TeamState`` with per-game fields reset."""

    return TeamState(
        lineup=list(base.lineup),
        bench=list(base.bench),
        pitchers=list(base.pitchers),
        team=base.team,
    )


# Global objects used by worker processes
_BASE_STATES: dict[str, TeamState] | None = None
_CFG: PlayBalanceConfig | None = None


def _init_pool(base_states: dict[str, TeamState], cfg: PlayBalanceConfig) -> None:
    """Initializer to share state across worker processes."""

    global _BASE_STATES, _CFG
    _BASE_STATES = base_states
    _CFG = cfg


def _simulate_game(home_id: str, away_id: str, seed: int) -> Counter[str]:
    """Simulate a single game and return stat totals for both teams."""

    assert _BASE_STATES is not None and _CFG is not None
    home = clone_team_state(_BASE_STATES[home_id])
    away = clone_team_state(_BASE_STATES[away_id])
    rng = random.Random(seed)
    sim = GameSimulation(home, away, _CFG, rng)
    sim.simulate_game()
    box = generate_boxscore(home, away)
    totals: Counter[str] = Counter()
    for side in ("home", "away"):
        batting = box[side]["batting"]
        pitching = box[side]["pitching"]
        totals["Runs"] += box[side]["score"]
        totals["Hits"] += sum(p["h"] for p in batting)
        totals["Doubles"] += sum(p["2b"] for p in batting)
        totals["Triples"] += sum(p["3b"] for p in batting)
        totals["HomeRuns"] += sum(p["hr"] for p in batting)
        totals["Walks"] += sum(p["bb"] for p in batting)
        totals["Strikeouts"] += sum(p["so"] for p in batting)
        totals["StolenBases"] += sum(p["sb"] for p in batting)
        totals["CaughtStealing"] += sum(p["cs"] for p in batting)
        totals["HitByPitch"] += sum(p["hbp"] for p in batting)
        totals["PlateAppearances"] += sum(p["pa"] for p in batting)
        totals["AtBats"] += sum(p["ab"] for p in batting)
        totals["SacFlies"] += sum(p.get("sf", 0) for p in batting)
        totals["GIDP"] += sum(p.get("gidp", 0) for p in batting)
        totals["TotalPitchesThrown"] += sum(p["pitches"] for p in pitching)
        totals["Strikes"] += sum(p["strikes"] for p in pitching)
    totals["TwoStrikeCounts"] += sim.two_strike_counts
    totals["ThreeBallCounts"] += sim.three_ball_counts
    return totals


def _simulate_game_star(args: tuple[str, str, int]) -> Counter[str]:
    """Helper to unpack arguments for ``imap_unordered``."""

    return _simulate_game(*args)


def simulate_season_average(
    use_tqdm: bool = True,
    seed: int | None = None,
) -> None:
    """Run a season simulation and print average box score values.

    Args:
        use_tqdm: Whether to display a progress bar using ``tqdm``.
        seed: Optional seed for deterministic simulations. If ``None`` (the
            default) a different random seed will be used on each run.
    """

    teams = [t.team_id for t in load_teams()]
    schedule_dir = get_base_dir() / "data" / "schedules"
    schedule_dir.mkdir(parents=True, exist_ok=True)
    schedule_file = schedule_dir / "2025_schedule.pkl"
    if schedule_file.exists():
        with schedule_file.open("rb") as fh:
            schedule = pickle.load(fh)
    else:
        schedule = generate_mlb_schedule(teams, date(2025, 4, 1))
        with schedule_file.open("wb") as fh:
            pickle.dump(schedule, fh)
    base_states = {tid: build_default_game_state(tid) for tid in teams}

    cfg = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")

    csv_path = (
        get_base_dir()
        / "data"
        / "MLB_avg"
        / "mlb_avg_boxscore_2020_2024_both_teams.csv"
    )
    with csv_path.open(newline="") as f:
        row = next(csv.DictReader(f))
    hits = float(row["Hits"])
    singles = (
        hits
        - float(row["Doubles"])
        - float(row["Triples"])
        - float(row["HomeRuns"])
    )
    cfg.hit1BProb = int(round(singles / hits * 100))
    cfg.hit2BProb = int(round(float(row["Doubles"]) / hits * 100))
    cfg.hit3BProb = int(round(float(row["Triples"]) / hits * 100))
    cfg.hitHRProb = max(
        0,
        100 - cfg.hit1BProb - cfg.hit2BProb - cfg.hit3BProb,
    )
    at_bats = float(row["AtBats"])
    walks = float(row["Walks"])
    hbp = float(row["HitByPitch"])
    total_pitches = float(row["TotalPitchesThrown"])
    strikeouts = float(row["Strikeouts"])
    homers = float(row["HomeRuns"])
    plate_appearances = at_bats + walks + hbp
    balls_in_play = at_bats - strikeouts - homers

    bench_path = (
        get_base_dir()
        / "data"
        / "MLB_avg"
        / "mlb_league_benchmarks_2025_filled.csv"
    )
    with bench_path.open(newline="") as bf:
        benchmarks = {
            r["metric_key"]: float(r["value"])
            for r in csv.DictReader(bf)
        }

    apply_league_benchmarks(cfg, benchmarks)
    mlb_averages = {stat: float(val) for stat, val in row.items() if stat}

    # Prepare list of (home, away, seed) tuples for multiprocessing
    rng = random.Random(seed)
    games = [
        (g["home"], g["away"], rng.randrange(2**32)) for g in schedule
    ]
    # Expect one schedule entry per game; duplicates would inflate averages.
    games_per_team = 162
    expected_games = len(teams) * games_per_team // 2
    if len(games) != expected_games:
        print(
            f"[Warning] Schedule length mismatch: expected {expected_games} games but got {len(games)}"
        )

    totals: Counter[str] = Counter()
    with mp.Pool(initializer=_init_pool, initargs=(base_states, cfg)) as pool:
        iterator = pool.imap_unordered(_simulate_game_star, games, chunksize=10)
        if use_tqdm:
            iterator = tqdm(iterator, total=len(games), desc="Simulating season")
        for game_totals in iterator:
            totals.update(game_totals)
    total_games = len(games)

    averages = {k: totals[k] / total_games for k in STAT_ORDER}

    diffs = {k: averages[k] - mlb_averages.get(k, 0.0) for k in STAT_ORDER}

    print("Average box score per game (both teams):")
    for key in STAT_ORDER:
        mlb_val = mlb_averages[key]
        sim_val = averages[key]
        diff = diffs[key]
        print(
            f"{key}: MLB {mlb_val:.2f}, Sim {sim_val:.2f}, Diff {diff:+.2f}"
        )

    total_pitches = totals["TotalPitchesThrown"]
    total_pa = totals.get("PlateAppearances", 0)
    p_pa = total_pitches / total_pa if total_pa else 0.0
    babip_den = (
        totals.get("AtBats", 0)
        - totals["Strikeouts"]
        - totals["HomeRuns"]
        + totals.get("SacFlies", 0)
    )
    babip = (
        (totals["Hits"] - totals["HomeRuns"]) / babip_den if babip_den else 0.0
    )
    dp_rate = totals.get("GIDP", 0) / babip_den if babip_den else 0.0
    print(f"Pitches/PA: {p_pa:.2f}")
    print(f"BABIP: {babip:.3f}")
    print(f"DoublePlayRate: {dp_rate:.3f}")
    print(f"Total two-strike counts: {totals['TwoStrikeCounts']}")
    print(f"Total three-ball counts: {totals['ThreeBallCounts']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simulate a full season and report average box score stats."
    )
    parser.add_argument(
        "--disable-tqdm",
        action="store_true",
        help="Disable tqdm progress bar.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for deterministic runs (default: random)",
    )
    args = parser.parse_args()

    env_disable = os.getenv("DISABLE_TQDM", "").lower() in {"1", "true", "yes"}
    use_tqdm = not (args.disable_tqdm or env_disable)
    configure_perf_tuning()
    simulate_season_average(
        use_tqdm=use_tqdm,
        seed=args.seed,
    )
