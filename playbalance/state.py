"""Basic state containers used across the play-balance engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PlayerState:
    """Representation of an active player with transient state."""

    name: str
    ratings: Dict[str, float] = field(default_factory=dict)
    position: str | None = None
    fatigue: float = 0.0
    stats: Dict[str, float] = field(default_factory=dict)


@dataclass
class BaseState:
    """Tracks which bases currently have runners."""

    first: bool = False
    second: bool = False
    third: bool = False

    def clear(self) -> None:
        """Remove all runners from the bases."""

        self.first = self.second = self.third = False

    def as_list(self) -> list[bool]:  # pragma: no cover - trivial
        return [self.first, self.second, self.third]

    def occupied(self) -> int:
        """Return the number of occupied bases."""

        return sum(self.as_list())


@dataclass
class GameState:
    """Simplified snapshot of a game's progress."""

    inning: int = 1
    top: bool = True
    outs: int = 0
    home_score: int = 0
    away_score: int = 0
    bases: BaseState = field(default_factory=BaseState)
    pitch_count: int = 0
    weather: Dict[str, float] = field(default_factory=dict)
    park_factors: Dict[str, float] = field(default_factory=dict)

    def advance_inning(self) -> None:
        """Advance to the next half-inning and reset counters."""

        self.top = not self.top
        if self.top:
            self.inning += 1
        self.outs = 0
        self.bases.clear()

    def score_run(self, home_team: bool) -> None:
        """Increment the score for the appropriate team."""

        if home_team:
            self.home_score += 1
        else:
            self.away_score += 1

    def record_pitch(self) -> None:
        """Increment the pitch counter."""

        self.pitch_count += 1


__all__ = ["PlayerState", "BaseState", "GameState"]
