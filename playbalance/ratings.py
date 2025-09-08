"""Utility functions for computing combined player ratings."""
from __future__ import annotations


def combine_offense(contact: float, power: float) -> float:
    """Return a naive offensive rating.

    This placeholder simply averages contact and power values. Future
    implementations will incorporate the extensive formulas defined in
    ``PBINI.txt``.
    """
    return (contact + power) / 2.0


def combine_slugging(power: float, discipline: float) -> float:
    """Return a naive slugging rating placeholder."""
    return (power * 0.7) + (discipline * 0.3)


def combine_defense(fielding: float, arm: float) -> float:
    """Return a naive defensive rating placeholder."""
    return (fielding + arm) / 2.0


__all__ = ["combine_offense", "combine_slugging", "combine_defense"]
