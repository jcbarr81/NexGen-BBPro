"""Collect batter decision diagnostics (swing/take/foul rates by count)."""
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

from playbalance.diagnostics.batter_decision import BatterDecisionTracker
from playbalance.orchestrator import _clone_team_state
from playbalance.sim_config import load_tuned_playbalance_config
from playbalance.simulation import GameSimulation
from utils.lineup_loader import build_default_game_state


@dataclass
class SampleTotals:
    tracker: BatterDecisionTracker
    totals: Counter

    def metrics(self) -> dict[str, float]:
        stats = Counter()
        for _, _, bucket in self.tracker.iter_rows():
            for key, value in bucket.items():
                stats[key] += value
        pitches = stats["pitches"]
        swings = stats["swings"]
        takes = stats["takes"]
        contact = stats["contact"]
        foul = stats["foul"]
        ball_in_play = stats["ball_in_play"]
        balls = stats["balls"]
        called_strikes = stats["called_strikes"]
        walks = stats["walks"]
        strikeouts = stats["strikeouts"]

        return {
            "pitches": pitches,
            "swing_rate": swings / pitches if pitches else 0.0,
            "take_rate": takes / pitches if pitches else 0.0,
            "contact_rate": contact / pitches if pitches else 0.0,
            "swing_contact_rate": contact / swings if swings else 0.0,
            "foul_rate": foul / pitches if pitches else 0.0,
            "ball_in_play_rate": ball_in_play / pitches if pitches else 0.0,
            "ball_rate": balls / pitches if pitches else 0.0,
            "called_strike_rate": called_strikes / pitches if pitches else 0.0,
            "walk_rate": walks / pitches if pitches else 0.0,
            "strikeout_rate": strikeouts / pitches if pitches else 0.0,
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
) -> SampleTotals:
    tracker = BatterDecisionTracker()
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
        sim.set_batter_decision_tracker(tracker)
        sim.simulate_game(persist_stats=False)

        for team in (home, away):
            totals["pa"] += sum(bs.pa for bs in team.lineup_stats.values())
            totals["bb"] += sum(bs.bb for bs in team.lineup_stats.values())
            totals["so"] += sum(bs.so for bs in team.lineup_stats.values())
            totals["h"] += sum(bs.h for bs in team.lineup_stats.values())

    return SampleTotals(tracker=tracker, totals=totals)


def _write_counts_csv(path: Path, tracker: BatterDecisionTracker) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "balls",
                "strikes",
                "pitches",
                "swings",
                "takes",
                "contact",
                "foul",
                "ball_in_play",
                "hits",
                "ball_calls",
                "called_strike_calls",
                "walks",
                "strikeouts",
                "hbp",
                "zone_pitches",
                "swing_rate",
                "take_rate",
                "foul_rate",
                "contact_rate",
                "swing_contact_rate",
                "ball_rate",
                "called_strike_rate",
            ]
        )
        for balls, strikes, stats in tracker.iter_rows():
            pitches = stats["pitches"]
            swings = stats["swings"]
            takes = stats["takes"]
            contact = stats["contact"]
            foul = stats["foul"]
            balls_cnt = stats["balls"]
            called = stats["called_strikes"]
            row = [
                balls,
                strikes,
                pitches,
                swings,
                takes,
                contact,
                stats["foul"],
                stats["ball_in_play"],
                stats["hits"],
                balls_cnt,
                called,
                stats["walks"],
                stats["strikeouts"],
                stats["hbp"],
                stats["zone_pitches"],
                swings / pitches if pitches else 0.0,
                takes / pitches if pitches else 0.0,
                foul / pitches if pitches else 0.0,
                contact / pitches if pitches else 0.0,
                (contact / swings) if swings else 0.0,
                balls_cnt / pitches if pitches else 0.0,
                called / pitches if pitches else 0.0,
            ]
            writer.writerow(row)


def _write_breakdown_csv(path: Path, tracker: BatterDecisionTracker) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pitch_kinds = ["sure strike", "close strike", "close ball", "sure ball"]
    components = [
        "base_lookup",
        "base_raw",
        "scale",
        "count_adjust",
        "close_ball_bonus",
        "discipline_adjust",
        "discipline_bias",
        "discipline_logit_offset",
        "close_strike_mix",
        "discipline_aggression",
        "discipline_aggression_input",
        "discipline_aggression_bias",
        "discipline_aggression_gain",
        "zone_protect_weight",
        "chase_protect_weight",
        "protect_scale",
        "discipline_zone_component",
        "discipline_chase_component",
        "discipline_zone_push",
        "discipline_chase_pull",
        "zone_bias",
        "chase_bias",
        "location_adjust",
        "take_bonus",
        "pre_two_strike",
        "two_strike_bonus",
        "final",
        "discipline",
        "discipline_raw",
        "discipline_raw_scaled",
        "discipline_norm",
        "discipline_clamped",
        "discipline_logit",
    ]
    headers = ["balls", "strikes", "samples"]
    headers.extend(f"avg_{comp}" for comp in components)
    headers.extend(f"pitch_kind_{kind.replace(' ', '_')}_pct" for kind in pitch_kinds)

    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        for balls, strikes, samples, averages, pitch_counts in tracker.iter_breakdown_rows():
            row = [balls, strikes, samples]
            for comp in components:
                row.append(averages.get(comp, 0.0))
            total = float(samples) if samples else 0.0
            for kind in pitch_kinds:
                pct = pitch_counts.get(kind, 0) / total if total else 0.0
                row.append(pct)
            writer.writerow(row)


def run(output_dir: Path) -> dict[str, dict]:
    base = Path(__file__).resolve().parents[1]
    players = base / "data" / "players.csv"
    rosters = base / "data" / "rosters"
    teams_file = base / "data" / "teams.csv"

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

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_counts_csv(output_dir / "batter_decisions_stochastic.csv", stochastic.tracker)
    _write_counts_csv(output_dir / "batter_decisions_deterministic.csv", deterministic.tracker)
    _write_breakdown_csv(
        output_dir / "batter_decision_breakdown_stochastic.csv", stochastic.tracker
    )
    _write_breakdown_csv(
        output_dir / "batter_decision_breakdown_deterministic.csv", deterministic.tracker
    )

    summary = {
        "stochastic": stochastic.metrics(),
        "deterministic": deterministic.metrics(),
    }
    with (output_dir / "batter_decisions_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect batter decision diagnostics.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/notes/batter_decisions"),
        help="Directory to store output files (default: docs/notes/batter_decisions)",
    )
    args = parser.parse_args()
    summary = run(args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
