"""State containers used across the play-balance engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PlayerState:
    """Representation of a player's dynamic state."""

    name: str
    ratings: Dict[str, float] = field(default_factory=dict)
    position: Optional[str] = None
    fatigue: float = 0.0


@dataclass
class BaseState:
    """Tracks which players occupy the bases."""

    first: Optional[PlayerState] = None
    second: Optional[PlayerState] = None
    third: Optional[PlayerState] = None


@dataclass
class TeamState:
    """Runtime information for a team participating in a game."""

    name: str
    lineup: List[PlayerState]
    bench: List[PlayerState] = field(default_factory=list)
    bullpen: List[PlayerState] = field(default_factory=list)
    lineup_index: int = 0


@dataclass
class GameState:
    """Simplified snapshot of a game's progress."""

    inning: int = 1
    half: str = "top"  # "top" or "bottom"
    outs: int = 0
    bases: BaseState = field(default_factory=BaseState)
    score: Dict[str, int] = field(default_factory=lambda: {"home": 0, "away": 0})
    teams: Dict[str, TeamState] = field(default_factory=dict)


__all__ = ["PlayerState", "BaseState", "TeamState", "GameState"]

