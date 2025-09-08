"""Generic probability utilities for the play-balance engine."""
from __future__ import annotations

from random import random, uniform
from typing import Dict, Sequence, TypeVar

T = TypeVar("T")


def roll(chance: float) -> bool:
    """Return ``True`` with the given probability.

    Parameters
    ----------
    chance:
        Probability in the range ``0.0``-``1.0``.
    """
    return random() < chance


def rand_range(low: float, high: float) -> float:
    """Return a random float between ``low`` and ``high``."""
    return uniform(low, high)


def clamp01(value: float) -> float:
    """Clamp ``value`` into the inclusive ``0.0``-``1.0`` range."""
    return max(0.0, min(1.0, value))


def chance_from_rating(rating: float, max_rating: float = 100.0) -> float:
    """Convert a ``rating`` into a probability value."""
    return clamp01(rating / max_rating)


def roll_rating(rating: float, max_rating: float = 100.0) -> bool:
    """Roll against a rating scaled to ``max_rating``."""
    return roll(chance_from_rating(rating, max_rating))


def weighted_choice(weights: Dict[T, float] | Sequence[float], items: Sequence[T] | None = None) -> T:
    """Select an item based on provided ``weights``.

    ``weights`` can be a mapping of item→weight or a sequence of weights with a
    parallel ``items`` sequence.
    """
    if isinstance(weights, dict):
        items, weights = zip(*weights.items())
    assert items is not None
    total = sum(weights)
    r = random() * total
    upto = 0.0
    for item, weight in zip(items, weights):
        upto += weight
        if upto >= r:
            return item
    # Fallback to last item (avoid mypy complaints)
    return items[-1]


__all__ = [
    "roll",
    "rand_range",
    "clamp01",
    "chance_from_rating",
    "roll_rating",
    "weighted_choice",
]
