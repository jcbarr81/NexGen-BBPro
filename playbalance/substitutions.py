"""Substitution utilities for the play-balance engine.

These helpers implement simplified substitution logic including pinch hitting,
bench running swaps, defensive replacements and basic bullpen management.
The real simulation engine contains additional nuance; the goal here is to
provide deterministic, easily-testable behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .ratings import combine_offense, combine_defense
from .state import PlayerState


@dataclass
class Team:
    """Minimal team container used by substitution helpers."""

    lineup: List[PlayerState]
    bench: List[PlayerState] = field(default_factory=list)
    bullpen: List[PlayerState] = field(default_factory=list)
    current_pitcher: PlayerState | None = None
    warming: PlayerState | None = None
    warmup_pitches: int = 0
    toasted: List[PlayerState] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rating helpers
# ---------------------------------------------------------------------------

def _off_rating(player: PlayerState, cfg) -> float:
    r = player.ratings
    return combine_offense(
        r.get("contact", 50), r.get("power", 50), r.get("discipline", 50), cfg
    )


def _def_rating(player: PlayerState, cfg) -> float:
    r = player.ratings
    return combine_defense(
        r.get("fielding", 50), r.get("arm", 50), r.get("range", 50), cfg
    )


# ---------------------------------------------------------------------------
# Bench substitutions
# ---------------------------------------------------------------------------

def pinch_hit(team: Team, index: int, cfg=None) -> PlayerState | None:
    """Replace the lineup player at ``index`` with the best bench hitter."""

    if not team.bench:
        return None
    current = team.lineup[index]
    best = max(team.bench, key=lambda p: _off_rating(p, cfg))
    if _off_rating(best, cfg) <= _off_rating(current, cfg):
        return None
    team.bench.remove(best)
    team.bench.append(current)
    team.lineup[index] = best
    return best


def pinch_run(team: Team, runner: PlayerState) -> PlayerState | None:
    """Return a faster bench player to pinch run for ``runner`` if available."""

    if not team.bench:
        return None
    best = max(team.bench, key=lambda p: p.ratings.get("speed", 0))
    if best.ratings.get("speed", 0) <= runner.ratings.get("speed", 0):
        return None
    team.bench.remove(best)
    team.bench.append(runner)
    return best


def defensive_sub(team: Team, index: int, cfg=None) -> PlayerState | None:
    """Replace the lineup player at ``index`` with the best defender."""

    if not team.bench:
        return None
    current = team.lineup[index]
    best = max(team.bench, key=lambda p: _def_rating(p, cfg))
    if _def_rating(best, cfg) <= _def_rating(current, cfg):
        return None
    team.bench.remove(best)
    team.bench.append(current)
    team.lineup[index] = best
    return best


def double_switch(
    team: Team, bat_index: int, field_index: int, cfg=None
) -> Tuple[PlayerState | None, PlayerState | None]:
    """Perform a double switch returning the hitters inserted at each spot."""

    hitter = pinch_hit(team, bat_index, cfg)
    fielder = defensive_sub(team, field_index, cfg)
    return hitter, fielder


# ---------------------------------------------------------------------------
# Pitcher management
# ---------------------------------------------------------------------------

def warm_reliever(
    team: Team, reliever_index: int = 0, warmup_pitch_count: int = 8
) -> bool:
    """Increment warm-up pitches for the selected reliever.

    Returns ``True`` once the reliever has thrown ``warmup_pitch_count`` pitches
    and is considered ready.  Warming a new reliever toasts the previously
    warmed pitcher if they were never used.
    """

    if reliever_index >= len(team.bullpen):
        return False
    reliever = team.bullpen[reliever_index]
    if team.warming is not reliever:
        if team.warming is not None:
            team.toasted.append(team.warming)
        team.warming = reliever
        team.warmup_pitches = 0
    team.warmup_pitches += 1
    return team.warmup_pitches >= warmup_pitch_count


def replace_pitcher(
    team: Team, fatigue_thresh: float, warmup_pitch_count: int = 8
) -> bool:
    """Replace the current pitcher with the warmed reliever if needed."""

    current = team.current_pitcher
    if current is None or current.fatigue < fatigue_thresh:
        return False
    if team.warming is None or team.warmup_pitches < warmup_pitch_count:
        return False
    reliever = team.warming
    team.bullpen.append(current)
    team.bullpen.remove(reliever)
    team.current_pitcher = reliever
    team.warming = None
    team.warmup_pitches = 0
    return True


def cool_down(team: Team) -> None:
    """Mark any warmed reliever as toasted and reset warm-up state."""

    if team.warming is not None:
        team.toasted.append(team.warming)
        team.warming = None
        team.warmup_pitches = 0


__all__ = [
    "Team",
    "pinch_hit",
    "pinch_run",
    "defensive_sub",
    "double_switch",
    "warm_reliever",
    "replace_pitcher",
    "cool_down",
]
