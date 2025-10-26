"""Helpers for injury rehab assignments.

Players on the disabled list can undertake rehab assignments at the AAA or
Low levels. Each simulated day increments their rehab tally which influences
when they are marked ``ready`` to return to the active roster.
"""

from __future__ import annotations

from typing import Literal, Optional

from models.player import Player

RehabLevel = Literal["aaa", "low"]
VALID_REHAB_LEVELS: tuple[str, ...] = ("aaa", "low")
REHAB_READY_DAYS = 5


def _normalize_level(level: str) -> RehabLevel:
    value = (level or "").strip().lower()
    if value == "aaa":
        return "aaa"
    if value in {"low", "a", "single-a"}:
        return "low"
    raise ValueError("Rehab assignments are limited to AAA or Low")


def assign_rehab(player: Player, level: str = "aaa") -> RehabLevel:
    """Start a rehab assignment for ``player`` at ``level``."""

    normalized = _normalize_level(level)
    if not getattr(player, "injured", False):
        raise ValueError("Player must be injured to begin a rehab assignment")
    player.injury_rehab_assignment = normalized
    player.injury_rehab_days = 0
    player.ready = False
    return normalized


def cancel_rehab(player: Player) -> None:
    """Clear any active rehab assignment for ``player``."""

    player.injury_rehab_assignment = None
    player.injury_rehab_days = 0


def advance_rehab_days(
    player: Player,
    days: int = 1,
    *,
    ready_threshold: int = REHAB_READY_DAYS,
) -> bool:
    """Increment rehab days and return ``True`` when the threshold is crossed."""

    if not getattr(player, "injury_rehab_assignment", None):
        return False
    try:
        delta = int(days)
    except (TypeError, ValueError):
        delta = 1
    delta = max(1, delta)
    previous = int(getattr(player, "injury_rehab_days", 0) or 0)
    player.injury_rehab_days = max(0, previous + delta)
    return previous < ready_threshold <= player.injury_rehab_days


def rehab_status(player: Player, *, ready_threshold: int = REHAB_READY_DAYS) -> Optional[str]:
    """Return a short string describing the player's rehab assignment."""

    assignment = getattr(player, "injury_rehab_assignment", None)
    if not assignment:
        return None
    days = int(getattr(player, "injury_rehab_days", 0) or 0)
    return f"{assignment.upper()} ({days}/{ready_threshold}d)"


__all__ = [
    "REHAB_READY_DAYS",
    "VALID_REHAB_LEVELS",
    "advance_rehab_days",
    "assign_rehab",
    "cancel_rehab",
    "rehab_status",
]
