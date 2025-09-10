"""Game simulation orchestrator for the play-balance engine.

This module stitches together the various play-balance helpers into a
simplified pitch-by-pitch simulation.  The implementation is intentionally
light‑weight: it focuses on wiring existing components rather than modelling
complete baseball rules.  Outcomes are generated using league benchmark
probabilities so that aggregate results mirror real‑world rates.

The orchestrator exposes helpers to simulate a single game or batches of games
representing a day, week, month or full season.  It can also be executed as a
stand‑alone script which prints key stat averages compared to the MLB
benchmarks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping
import argparse
import random

from .config import PlayBalanceConfig, load_config
from .state import GameState
from .pitcher_ai import select_pitch
from .batter_ai import StrikeZoneGrid, look_for_zone
from .benchmarks import load_benchmarks, league_average
from .player_loader import Player, load_lineup, load_pitching_staff, load_players


BASE_DIR = Path(__file__).resolve().parents[1]


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

    def as_dict(self) -> Dict[str, int]:  # pragma: no cover - convenience
        # Convert dataclass fields into a plain dictionary.  The method is
        # excluded from coverage as it is a simple convenience wrapper.
        return {
            "pa": self.pa,
            "k": self.k,
            "bb": self.bb,
            "hits": self.hits,
            "bip": self.bip,
            "sb_attempts": self.sb_attempts,
            "sb_success": self.sb_success,
            "pitches": self.pitches,
        }


# ---------------------------------------------------------------------------
# Team representation
# ---------------------------------------------------------------------------


@dataclass
class Team:
    """Simple container for a team's roster information."""

    lineup: list[Player]
    pitchers: list[Player]


def _load_default_teams() -> tuple[Team, Team]:
    """Load example teams from the application's CSV data.

    The function pulls player ratings, lineups and pitching staffs from the
    ``data`` directory so that simulations use the real application rosters by
    default.  Minimal fallbacks are applied when files are missing to keep the
    helpers usable in tests.
    """

    data_dir = BASE_DIR / "data"
    players = load_players(data_dir / "players.csv")
    home_lineup = load_lineup(data_dir / "lineups/ARG_vs_rhp.csv", players)
    away_lineup = load_lineup(data_dir / "lineups/ARG_vs_rhp.csv", players)
    if not home_lineup:
        home_lineup = [p for p in players.values() if not p.is_pitcher][:9]
    if not away_lineup:
        away_lineup = [p for p in players.values() if not p.is_pitcher][9:18]

    home_pitchers = load_pitching_staff(data_dir / "rosters/ABU.csv", players)
    away_pitchers = load_pitching_staff(data_dir / "rosters/BCH.csv", players)
    if not home_pitchers:
        home_pitchers = [p for p in players.values() if p.is_pitcher][:5]
    if not away_pitchers:
        away_pitchers = [p for p in players.values() if p.is_pitcher][5:10]

    return Team(home_lineup, home_pitchers), Team(away_lineup, away_pitchers)


# ---------------------------------------------------------------------------
# Core simulation helpers
# ---------------------------------------------------------------------------


def _simulate_plate_appearance(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    rng: random.Random,
    game_state: GameState,
    pitcher: Player,
    batter: Player,
) -> str:
    """Simulate a single plate appearance and return its outcome.

    Outcomes are one of ``"walk"``, ``"strikeout"``, ``"hit"`` or ``"out"``.
    A small pitch loop is executed to exercise the pitcher and batter helpers
    while the ultimate result is determined by league-average probabilities.
    """

    # Derive a typical pitch count for the appearance to exercise pitcher/batter
    # helpers even though the ultimate outcome is probability driven.
    pitches_per_pa = max(1, int(round(league_average(benchmarks, "pitches_per_pa", 4))))
    # Ensure configuration holds a dictionary for objective weights so lookups
    # within the AI helpers do not fail.
    if not isinstance(getattr(cfg, "pitchObjectiveWeights", {}), dict):
        cfg.pitchObjectiveWeights = {}
    grid = StrikeZoneGrid()
    pitch_ratings = {
        "fastball": pitcher.ratings.get("fastball", 50.0),
        "slider": pitcher.ratings.get("slider", 50.0),
    }
    batter_dis = batter.ratings.get("discipline", 50.0)
    for _ in range(pitches_per_pa):
        select_pitch(cfg, pitch_ratings, rng=rng)
        look_for_zone(cfg, balls=0, strikes=0, batter_dis=batter_dis, grid=grid)
        game_state.record_pitch()

    roll = rng.random()
    bb_threshold = league_average(benchmarks, "bb_pct")
    k_threshold = bb_threshold + league_average(benchmarks, "k_pct")
    b_contact = batter.ratings.get("contact", 50.0)
    p_control = pitcher.ratings.get("control", 50.0)
    p_movement = pitcher.ratings.get("movement", 50.0)
    stuff = (pitch_ratings["fastball"] + pitch_ratings["slider"]) / 2.0
    bb_threshold += (batter_dis - p_control) / 1000.0
    k_threshold += (stuff - b_contact) / 1000.0
    bb_threshold = max(0.0, min(1.0, bb_threshold))
    k_threshold = max(bb_threshold, min(1.0, k_threshold))
    if roll < bb_threshold:
        return "walk"
    if roll < k_threshold:
        return "strikeout"
    # Ball put in play.
    game_state.pitch_count += 1  # account for contact pitch
    game_state.bases  # access to satisfy state usage even though simplified
    babip = league_average(benchmarks, "babip")
    babip += (b_contact - p_movement) / 1000.0
    babip = max(0.0, min(1.0, babip))
    if rng.random() < babip:
        return "hit"
    return "out"


def simulate_game(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    home_team: Team,
    away_team: Team,
    rng: random.Random | None = None,
) -> SimulationResult:
    """Simulate a single game returning aggregate statistics."""

    rng = rng or random.Random()
    state = GameState()
    stats = SimulationResult()
    away_idx = 0
    home_idx = 0
    away_pitcher = away_team.pitchers[0]
    home_pitcher = home_team.pitchers[0]
    away_outs = 0
    home_outs = 0

    while away_outs < 27 or home_outs < 27:
        if state.top:
            batter = away_team.lineup[away_idx]
            pitcher = home_pitcher
            away_idx = (away_idx + 1) % len(away_team.lineup)
        else:
            batter = home_team.lineup[home_idx]
            pitcher = away_pitcher
            home_idx = (home_idx + 1) % len(home_team.lineup)
        outcome = _simulate_plate_appearance(cfg, benchmarks, rng, state, pitcher, batter)
        stats.pa += 1
        if outcome == "walk":
            stats.bb += 1
            if rng.random() < league_average(benchmarks, "sba_per_pa"):
                stats.sb_attempts += 1
                if rng.random() < league_average(benchmarks, "sb_pct"):
                    stats.sb_success += 1
                else:
                    state.outs += 1
        elif outcome == "strikeout":
            stats.k += 1
            state.outs += 1
            if state.top:
                away_outs += 1
            else:
                home_outs += 1
        elif outcome == "hit":
            stats.hits += 1
            stats.bip += 1
            if rng.random() < league_average(benchmarks, "sba_per_pa"):
                stats.sb_attempts += 1
                if rng.random() < league_average(benchmarks, "sb_pct"):
                    stats.sb_success += 1
                else:
                    state.outs += 1
                    if state.top:
                        away_outs += 1
                    else:
                        home_outs += 1
        else:  # out on ball in play
            stats.bip += 1
            state.outs += 1
            if state.top:
                away_outs += 1
            else:
                home_outs += 1

        if state.outs >= 3:
            state.advance_inning()

    stats.pitches = state.pitch_count
    return stats


def _combine_results(results: Iterable[SimulationResult]) -> SimulationResult:
    combined = SimulationResult()
    for res in results:
        combined.pa += res.pa
        combined.k += res.k
        combined.bb += res.bb
        combined.hits += res.hits
        combined.bip += res.bip
        combined.sb_attempts += res.sb_attempts
        combined.sb_success += res.sb_success
        combined.pitches += res.pitches
    return combined


def simulate_games(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    games: int,
    home_team: Team | None = None,
    away_team: Team | None = None,
    rng_seed: int | None = None,
) -> SimulationResult:
    """Simulate ``games`` games and return aggregated statistics."""

    if home_team is None or away_team is None:
        home_team, away_team = _load_default_teams()

    rng = random.Random(rng_seed)
    results = []
    for i in range(games):
        home_pitcher = home_team.pitchers[i % len(home_team.pitchers)]
        away_pitcher = away_team.pitchers[i % len(away_team.pitchers)]
        game_home = Team(home_team.lineup, [home_pitcher])
        game_away = Team(away_team.lineup, [away_pitcher])
        results.append(simulate_game(cfg, benchmarks, game_home, game_away, rng))
    return _combine_results(results)


# Public helpers mapping to typical season progress increments -----------------

def simulate_day(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    home_team: Team | None = None,
    away_team: Team | None = None,
    *,
    rng_seed: int | None = None,
) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 1, home_team, away_team, rng_seed=rng_seed)


def simulate_week(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    home_team: Team | None = None,
    away_team: Team | None = None,
    *,
    rng_seed: int | None = None,
) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 7, home_team, away_team, rng_seed=rng_seed)


def simulate_month(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    home_team: Team | None = None,
    away_team: Team | None = None,
    *,
    rng_seed: int | None = None,
) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 30, home_team, away_team, rng_seed=rng_seed)


def simulate_season(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    home_team: Team | None = None,
    away_team: Team | None = None,
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

    cfg = load_config()
    benchmarks = load_benchmarks()
    home_team, away_team = _load_default_teams()

    stats = simulate_games(
        cfg, benchmarks, args.games, home_team, away_team, rng_seed=args.seed
    )

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
    "simulate_game",
    "simulate_games",
    "simulate_day",
    "simulate_week",
    "simulate_month",
    "simulate_season",
    "Team",
    "main",
]
