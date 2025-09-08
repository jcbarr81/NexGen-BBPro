"""Utility functions for computing and converting player ratings."""
from __future__ import annotations


def clamp_rating(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a rating between ``minimum`` and ``maximum``."""
    return max(minimum, min(maximum, value))


def rating_to_pct(rating: float, maximum: float = 100.0) -> float:
    """Convert a ``rating`` to a probability-like percentage (0-1)."""
    rating = clamp_rating(rating, 0.0, maximum)
    return rating / maximum


def combine_offense(contact: float, power: float, discipline: float) -> float:
    """Return a composite offensive rating.

    Weights roughly follow common sabermetric intuition where contact and power
    drive most of the offensive value while plate discipline provides a
    supporting role.
    """
    return (contact * 0.4) + (power * 0.4) + (discipline * 0.2)


def combine_slugging(power: float, discipline: float, contact: float) -> float:
    """Return a composite slugging rating."""
    return (power * 0.5) + (discipline * 0.2) + (contact * 0.3)


def combine_defense(fielding: float, arm: float, range_rating: float) -> float:
    """Return a composite defensive rating."""
    return (fielding * 0.5) + (arm * 0.3) + (range_rating * 0.2)


__all__ = [
    "clamp_rating",
    "rating_to_pct",
    "combine_offense",
    "combine_slugging",
    "combine_defense",
]
