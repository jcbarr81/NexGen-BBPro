"""Basic state containers used across the play-balance engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PlayerState:
    """Minimal representation of an active player."""

    name: str
    ratings: Dict[str, float] = field(default_factory=dict)


@dataclass
class GameState:
    """Simplified snapshot of a game's progress."""

    inning: int = 1
    outs: int = 0
    home_score: int = 0
    away_score: int = 0


__all__ = ["PlayerState", "GameState"]
