"""Season simulation orchestrator built on the full game engine.

This module delegates game resolution to :class:`logic.season_simulator.SeasonSimulator`
so that pitching staffs and lineups naturally rotate following season rules.
Aggregated league statistics are collected from generated box scores which
mirror real MLB rates when using the tuned play‑balance configuration.

The public helpers simulate a specified number of games by generating a simple
schedule for two example teams.  Convenience wrappers are provided for common
progression increments like a day, week, month or full 162 game season.  When
executed as a script the module prints key stat averages compared to MLB
benchmarks.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Mapping, Any
import argparse
import random

from logic.schedule_generator import generate_mlb_schedule
from logic.season_simulator import SeasonSimulator
from logic.simulation import (
    FieldingState,
    GameSimulation,
    PitcherState,
    TeamState,
    generate_boxscore,
)
from logic.sim_config import load_tuned_playbalance_config
from playbalance.benchmarks import load_benchmarks, league_average
from utils.lineup_loader import build_default_game_state


@dataclass
class SimulationResult:
    """Aggregated statistics from simulated games."""

    pa: int = 0
    k: int = 0
    bb: int = 0
    hits: int = 0
    bip: int = 0
    sb_attempts: int = 0
    sb_success: int = 0
    pitches: int = 0


def _clone_team_state(base: TeamState) -> TeamState:
    """Return a deep-copied ``TeamState`` with per-game fields reset."""

    team = deepcopy(base)
    team.lineup_stats = {}
    team.pitcher_stats = {}
    team.fielding_stats = {}
    team.batting_index = 0
    team.bases = [None, None, None]
    team.base_pitchers = [None, None, None]
    team.runs = 0
    team.inning_runs = []
    team.lob = 0
    team.inning_lob = []
    team.inning_events = []
    team.team_stats = {}
    team.warming_reliever = False
    team.bullpen_warmups = {}
    if team.pitchers:
        starter = team.pitchers[0]
        ps = PitcherState(starter)
        team.pitcher_stats[starter.player_id] = ps
        team.current_pitcher_state = ps
        ps.g += 1
        ps.gs += 1
        fs = team.fielding_stats.setdefault(starter.player_id, FieldingState(starter))
        fs.g += 1
        fs.gs += 1
    else:
        team.current_pitcher_state = None
    for p in team.lineup:
        fs = team.fielding_stats.setdefault(p.player_id, FieldingState(p))
        fs.g += 1
        fs.gs += 1
    return team


# ---------------------------------------------------------------------------
# Core simulation helpers
# ---------------------------------------------------------------------------


def simulate_games(
    cfg: Any | None,
    benchmarks: Mapping[str, float] | None,
    games: int,
    home_team: Any | None = None,
    away_team: Any | None = None,
    *,
    rng_seed: int | None = None,
) -> SimulationResult:
    """Simulate ``games`` games and return aggregated statistics.

    The provided configuration and benchmark mappings are accepted for
    backwards compatibility but are not directly used.  A minimal league
    schedule is generated for two example teams (``ARG`` and ``BCH``) and the
    full :class:`SeasonSimulator` drives day-by-day simulation.  Box score
    totals are accumulated across all games to produce league-wide statistics.
    """

    team_ids = ["ABU", "BCH"]
    schedule = generate_mlb_schedule(team_ids, date(2025, 4, 1), games_per_team=games)
    base_dir = Path(__file__).resolve().parents[1]
    players_file = base_dir / "data" / "players.csv"
    roster_dir = base_dir / "data" / "rosters"
    base_states = {
        tid: build_default_game_state(tid, str(players_file), str(roster_dir))
        for tid in team_ids
    }
    if cfg is None:
        cfg, _ = load_tuned_playbalance_config()
    rng = random.Random(rng_seed)
    totals: Counter[str] = Counter()

    def _simulate_game(home_id: str, away_id: str) -> tuple[int, int]:
        home = _clone_team_state(base_states[home_id])
        away = _clone_team_state(base_states[away_id])
        sim = GameSimulation(home, away, cfg, rng)
        sim.simulate_game()
        box = generate_boxscore(home, away)
        for side in ("home", "away"):
            batting = box[side]["batting"]
            pitching = box[side]["pitching"]
            totals["pa"] += sum(p["pa"] for p in batting)
            totals["bb"] += sum(p["bb"] for p in batting)
            totals["k"] += sum(p["so"] for p in batting)
            totals["h"] += sum(p["h"] for p in batting)
            totals["hr"] += sum(p["hr"] for p in batting)
            totals["ab"] += sum(p["ab"] for p in batting)
            totals["sf"] += sum(p.get("sf", 0) for p in batting)
            totals["sb"] += sum(p["sb"] for p in batting)
            totals["cs"] += sum(p["cs"] for p in batting)
            totals["pitches"] += sum(p["pitches"] for p in pitching)
        # Rotate starting pitchers for next appearances
        base_states[home_id].pitchers = base_states[home_id].pitchers[1:] + base_states[home_id].pitchers[:1]
        base_states[away_id].pitchers = base_states[away_id].pitchers[1:] + base_states[away_id].pitchers[:1]
        return box["home"]["score"], box["away"]["score"]

    simulator = SeasonSimulator(schedule, simulate_game=_simulate_game)
    for _ in simulator.dates:
        simulator.simulate_next_day()

    bip = totals["ab"] - totals["k"] - totals["hr"] + totals["sf"]
    sb_attempts = totals["sb"] + totals["cs"]
    return SimulationResult(
        pa=totals["pa"],
        k=totals["k"],
        bb=totals["bb"],
        hits=totals["h"],
        bip=bip,
        sb_attempts=sb_attempts,
        sb_success=totals["sb"],
        pitches=totals["pitches"],
    )


# Public helpers mapping to typical season progress increments -----------------

def simulate_day(
    cfg: Any,
    benchmarks: Mapping[str, float],
    home_team: Any | None = None,
    away_team: Any | None = None,
    *,
    rng_seed: int | None = None,
) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 1, home_team, away_team, rng_seed=rng_seed)


def simulate_week(
    cfg: Any,
    benchmarks: Mapping[str, float],
    home_team: Any | None = None,
    away_team: Any | None = None,
    *,
    rng_seed: int | None = None,
) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 7, home_team, away_team, rng_seed=rng_seed)


def simulate_month(
    cfg: Any,
    benchmarks: Mapping[str, float],
    home_team: Any | None = None,
    away_team: Any | None = None,
    *,
    rng_seed: int | None = None,
) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 30, home_team, away_team, rng_seed=rng_seed)


def simulate_season(
    cfg: Any,
    benchmarks: Mapping[str, float],
    home_team: Any | None = None,
    away_team: Any | None = None,
    *,
    games: int = 162,
    rng_seed: int | None = None,
) -> SimulationResult:
    return simulate_games(cfg, benchmarks, games, home_team, away_team, rng_seed=rng_seed)


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate games using the play-balance engine")
    parser.add_argument("--games", type=int, default=1, help="number of games to simulate")
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducibility")
    args = parser.parse_args(argv)

    cfg, _ = load_tuned_playbalance_config()
    benchmarks = load_benchmarks()
    stats = simulate_games(cfg, benchmarks, args.games, rng_seed=args.seed)

    pa = stats.pa or 1
    k_pct = stats.k / pa
    bb_pct = stats.bb / pa
    babip = stats.hits / stats.bip if stats.bip else 0.0
    sba_rate = stats.sb_attempts / pa
    sb_pct = stats.sb_success / stats.sb_attempts if stats.sb_attempts else 0.0

    print("Simulated Games:", args.games)
    print(f"K%:  {k_pct:.3f} (MLB {league_average(benchmarks, 'k_pct'):.3f})")
    print(f"BB%: {bb_pct:.3f} (MLB {league_average(benchmarks, 'bb_pct'):.3f})")
    print(f"BABIP: {babip:.3f} (MLB {league_average(benchmarks, 'babip'):.3f})")
    print(f"SB Attempt/PA: {sba_rate:.3f} (MLB {league_average(benchmarks, 'sba_per_pa'):.3f})")
    print(f"SB%: {sb_pct:.3f} (MLB {league_average(benchmarks, 'sb_pct'):.3f})")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())


__all__ = [
    "SimulationResult",
    "simulate_games",
    "simulate_day",
    "simulate_week",
    "simulate_month",
    "simulate_season",
    "main",
]
