"""Utility helpers for computing combined player ratings.

These functions are intentionally light-weight; they provide reasonably
documented behaviour without yet replicating all of the formulas contained in
``PBINI.txt``.  The helpers will be expanded as later modules require more
fidelity.
"""
from __future__ import annotations


def clamp_rating(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp ``value`` between ``minimum`` and ``maximum``."""

    return max(minimum, min(maximum, value))


def combine_offense(contact: float, power: float, discipline: float = 50.0) -> float:
    """Return a blended offensive rating on a ``0``-``100`` scale."""

    rating = (contact * 0.5) + (power * 0.4) + (discipline * 0.1)
    return clamp_rating(rating)


def combine_slugging(power: float, discipline: float) -> float:
    """Return a blended slugging rating on a ``0``-``100`` scale."""

    rating = (power * 0.8) + (discipline * 0.2)
    return clamp_rating(rating)


def combine_defense(fielding: float, arm: float, range_: float = 50.0) -> float:
    """Return a blended defensive rating on a ``0``-``100`` scale."""

    rating = (fielding * 0.6) + (arm * 0.3) + (range_ * 0.1)
    return clamp_rating(rating)


__all__ = [
    "clamp_rating",
    "combine_offense",
    "combine_slugging",
    "combine_defense",
]
