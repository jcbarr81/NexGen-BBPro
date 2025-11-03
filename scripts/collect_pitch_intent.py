"""Collect pitch intent diagnostics for the legacy simulation engine.

The script runs two samples with calibration disabled:

1. A 200-game stochastic sweep with varied RNG seeds.
2. A 10-game deterministic harness (seeded) for reproducibility.

Outputs:
    - Bucket counts CSV (balls, strikes, bucket, count, pct_total, pct_count)
    - Objective counts CSV
    - JSON summary containing aggregate metrics and bucket shares
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from playbalance.diagnostics.pitch_intent import PitchIntentTracker
from playbalance.orchestrator import _clone_team_state
from playbalance.sim_config import load_tuned_playbalance_config
from playbalance.simulation import GameSimulation
from utils.lineup_loader import build_default_game_state


@dataclass
class SampleResult:
    tracker: PitchIntentTracker
    totals: Counter

    @property
    def pa(self) -> int:
        return int(self.totals.get("pa", 0))

    @property
    def pitches(self) -> int:
        return int(self.totals.get("pitches", 0))

    def metrics(self) -> dict[str, float]:
        pa = self.pa
        pitches = self.pitches
        swings = self.totals.get("swings", 0)
        zone_pitches = self.totals.get("zone_pitches", 0)
        zone_swings = self.totals.get("zone_swings", 0)
        strikes = self.totals.get("strikes", 0)
        so = self.totals.get("so", 0)
        so_swinging = self.totals.get("so_swinging_pitch", 0)
        bb = self.totals.get("bb", 0)
        hbp = self.totals.get("hbp", 0)
        bip_final = self.totals.get("bip_final", 0)
        fps = self.totals.get("first_pitch_strikes", 0)
        bf = self.totals.get("batters_faced", 0)

        called_strikes = max(zone_pitches - zone_swings, 0)
        foul_est = max(strikes - called_strikes - so_swinging, 0)
        swing_strike_est = max(strikes - called_strikes - foul_est, 0)

        return {
            "pitches_per_pa": (pitches / pa) if pa else 0.0,
            "swing_rate": (swings / pitches) if pitches else 0.0,
            "take_rate": (1 - swings / pitches) if pitches else 0.0,
            "strikeout_pct": (so / pa) if pa else 0.0,
            "walk_pct": (bb / pa) if pa else 0.0,
            "first_pitch_strike_pct": (fps / bf) if bf else 0.0,
            "called_strike_pct": (called_strikes / pitches) if pitches else 0.0,
            "foul_share_est": (foul_est / pitches) if pitches else 0.0,
            "swinging_strike_pct": (swing_strike_est / pitches) if pitches else 0.0,
            "contact_rate_pa": ((pa - so) / pa) if pa else 0.0,
            "bip_final_pct": (bip_final / pa) if pa else 0.0,
        }


def _disable_calibration(cfg) -> None:
    cfg.pitchCalibrationEnabled = 0
    if hasattr(cfg, "values"):
        cfg.values["pitchCalibrationEnabled"] = 0
    if hasattr(cfg, "targetPitchesPerPA"):
        cfg.targetPitchesPerPA = 0
    if hasattr(cfg, "values"):
        cfg.values["targetPitchesPerPA"] = 0


def _collect_sample(
    *,
    num_games: int,
    seed: int,
    deterministic: bool,
    home_base,
    away_base,
) -> SampleResult:
    tracker = PitchIntentTracker()
    totals: Counter = Counter()

    cfg, _ = load_tuned_playbalance_config()
    _disable_calibration(cfg)

    home_len = max(1, len(home_base.pitchers))
    away_len = max(1, len(away_base.pitchers))
    rotation_idx = {"home": 0, "away": 0}

    rng = random.Random(seed)

    for game_index in range(num_games):
        home = _clone_team_state(home_base)
        away = _clone_team_state(away_base)

        if home.pitchers:
            rot = rotation_idx["home"]
            home.pitchers = home.pitchers[rot:] + home.pitchers[:rot]
            rotation_idx["home"] = (rot + 1) % home_len
        if away.pitchers:
            rot = rotation_idx["away"]
            away.pitchers = away.pitchers[rot:] + away.pitchers[:rot]
            rotation_idx["away"] = (rot + 1) % away_len

        game_seed = seed + game_index if deterministic else rng.randrange(2**32)
        sim = GameSimulation(home, away, cfg, random.Random(game_seed))
        sim.pitcher_ai.set_intent_tracker(tracker)
        sim.simulate_game(persist_stats=False)

        for team in (home, away):
            for ps in team.pitcher_stats.values():
                totals["pitches"] += ps.pitches_thrown
                totals["strikes"] += ps.strikes_thrown
                totals["zone_pitches"] += ps.zone_pitches
                totals["zone_swings"] += ps.zone_swings
                totals["swings"] += ps.zone_swings + ps.o_zone_swings
                totals["so_swinging_pitch"] += ps.so_swinging
                totals["first_pitch_strikes"] += ps.first_pitch_strikes
                totals["batters_faced"] += ps.bf
            totals["pa"] += sum(bs.pa for bs in team.lineup_stats.values())
            totals["bb"] += sum(bs.bb for bs in team.lineup_stats.values())
            totals["so"] += sum(bs.so for bs in team.lineup_stats.values())
            totals["hbp"] += sum(bs.hbp for bs in team.lineup_stats.values())
            totals["bip_final"] += sum(
                bs.pa - bs.bb - bs.so - bs.hbp for bs in team.lineup_stats.values()
            )

    return SampleResult(tracker=tracker, totals=totals)


def _write_bucket_csv(path: Path, tracker: PitchIntentTracker) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["balls", "strikes", "bucket", "count", "pct_total", "pct_for_count"]
        )
        count_totals: dict[tuple[int, int], int] = {}
        for (balls, strikes, _bucket), count in tracker.bucket_counts.items():
            key = (balls, strikes)
            count_totals[key] = count_totals.get(key, 0) + count
        overall_total = tracker.total or 1
        for (balls, strikes, bucket), count in sorted(
            tracker.bucket_counts.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2]),
        ):
            pct_total = count / overall_total
            pair_total = count_totals.get((balls, strikes), 1) or 1
            pct_for_count = count / pair_total
            writer.writerow([balls, strikes, bucket, count, pct_total, pct_for_count])


def _write_objective_csv(path: Path, tracker: PitchIntentTracker) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["balls", "strikes", "objective", "count"])
        for row in sorted(
            tracker.iter_objective_rows(), key=lambda item: (item[0], item[1], item[2])
        ):
            writer.writerow(row)


def run(output_dir: Path) -> dict[str, dict]:
    base_dir = Path(__file__).resolve().parents[1]
    players = base_dir / "data" / "players.csv"
    rosters = base_dir / "data" / "rosters"
    teams_file = base_dir / "data" / "teams.csv"

    home_base = build_default_game_state(
        "ABU", players_file=str(players), roster_dir=str(rosters), teams_file=str(teams_file)
    )
    away_base = build_default_game_state(
        "BCH", players_file=str(players), roster_dir=str(rosters), teams_file=str(teams_file)
    )

    stochastic = _collect_sample(
        num_games=200,
        seed=2025,
        deterministic=False,
        home_base=home_base,
        away_base=away_base,
    )
    deterministic = _collect_sample(
        num_games=10,
        seed=2025,
        deterministic=True,
        home_base=home_base,
        away_base=away_base,
    )

    summary = {
        "stochastic": stochastic.metrics(),
        "deterministic": deterministic.metrics(),
        "stochastic_bucket_share": stochastic.tracker.percentage_by_bucket(),
        "deterministic_bucket_share": deterministic.tracker.percentage_by_bucket(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_bucket_csv(output_dir / "pitch_intent_buckets_stochastic.csv", stochastic.tracker)
    _write_bucket_csv(output_dir / "pitch_intent_buckets_deterministic.csv", deterministic.tracker)
    _write_objective_csv(
        output_dir / "pitch_intent_objectives_stochastic.csv", stochastic.tracker
    )
    _write_objective_csv(
        output_dir / "pitch_intent_objectives_deterministic.csv", deterministic.tracker
    )

    with (output_dir / "pitch_intent_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect pitch intent diagnostics.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/notes/pitch_intent"),
        help="Directory to store output CSV/JSON files (default: docs/notes/pitch_intent)",
    )
    args = parser.parse_args()
    summary = run(args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
