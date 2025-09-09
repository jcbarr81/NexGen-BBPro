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
from typing import Dict, Iterable, Mapping
import argparse
import random

from .config import PlayBalanceConfig, load_config
from .state import GameState
from .pitcher_ai import select_pitch
from .batter_ai import StrikeZoneGrid, look_for_zone
from .benchmarks import load_benchmarks, league_average


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
# Core simulation helpers
# ---------------------------------------------------------------------------


def _simulate_plate_appearance(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    rng: random.Random,
    game_state: GameState,
) -> str:
    """Simulate a single plate appearance and return its outcome.

    Outcomes are one of ``"walk"``, ``"strikeout"``, ``"hit"`` or ``"out"``.
    A small pitch loop is executed to exercise the pitcher and batter helpers
    while the ultimate result is determined by league-average probabilities.
    """

    pitches_per_pa = max(1, int(round(league_average(benchmarks, "pitches_per_pa", 4))))
    if not isinstance(getattr(cfg, "pitchObjectiveWeights", {}), dict):
        cfg.pitchObjectiveWeights = {}
    grid = StrikeZoneGrid()
    for _ in range(pitches_per_pa):
        # Use placeholder ratings to drive the helpers.
        select_pitch(cfg, {"fastball": 50.0, "slider": 50.0}, rng=rng)
        look_for_zone(cfg, balls=0, strikes=0, batter_dis=50.0, grid=grid)
        game_state.record_pitch()

    roll = rng.random()
    bb_threshold = league_average(benchmarks, "bb_pct")
    k_threshold = bb_threshold + league_average(benchmarks, "k_pct")
    if roll < bb_threshold:
        return "walk"
    if roll < k_threshold:
        return "strikeout"
    # Ball put in play.
    game_state.pitch_count += 1  # account for contact pitch
    game_state.bases  # access to satisfy state usage even though simplified
    if rng.random() < league_average(benchmarks, "babip"):
        return "hit"
    return "out"


def simulate_game(
    cfg: PlayBalanceConfig,
    benchmarks: Mapping[str, float],
    rng: random.Random | None = None,
) -> SimulationResult:
    """Simulate a single game returning aggregate statistics."""

    rng = rng or random.Random()
    state = GameState()
    stats = SimulationResult()

    while state.outs < 27:
        outcome = _simulate_plate_appearance(cfg, benchmarks, rng, state)
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
        elif outcome == "hit":
            stats.hits += 1
            stats.bip += 1
            if rng.random() < league_average(benchmarks, "sba_per_pa"):
                stats.sb_attempts += 1
                if rng.random() < league_average(benchmarks, "sb_pct"):
                    stats.sb_success += 1
                else:
                    state.outs += 1
        else:  # out on ball in play
            stats.bip += 1
            state.outs += 1

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
    rng_seed: int | None = None,
) -> SimulationResult:
    """Simulate ``games`` games and return aggregated statistics."""

    rng = random.Random(rng_seed)
    results = [simulate_game(cfg, benchmarks, rng) for _ in range(games)]
    return _combine_results(results)


# Public helpers mapping to typical season progress increments -----------------

def simulate_day(cfg: PlayBalanceConfig, benchmarks: Mapping[str, float], *, rng_seed: int | None = None) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 1, rng_seed=rng_seed)


def simulate_week(cfg: PlayBalanceConfig, benchmarks: Mapping[str, float], *, rng_seed: int | None = None) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 7, rng_seed=rng_seed)


def simulate_month(cfg: PlayBalanceConfig, benchmarks: Mapping[str, float], *, rng_seed: int | None = None) -> SimulationResult:
    return simulate_games(cfg, benchmarks, 30, rng_seed=rng_seed)


def simulate_season(cfg: PlayBalanceConfig, benchmarks: Mapping[str, float], *, games: int = 162, rng_seed: int | None = None) -> SimulationResult:
    return simulate_games(cfg, benchmarks, games, rng_seed=rng_seed)


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
    "simulate_game",
    "simulate_games",
    "simulate_day",
    "simulate_week",
    "simulate_month",
    "simulate_season",
    "main",
]
