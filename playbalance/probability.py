"""Generic probability utilities for the play-balance engine."""
from __future__ import annotations

from random import random
from typing import Dict, Sequence, TypeVar

T = TypeVar("T")


def clamp01(value: float) -> float:
    """Clamp ``value`` to the inclusive ``0.0``–``1.0`` range."""

    return max(0.0, min(1.0, value))


def roll(chance: float) -> bool:
    """Return ``True`` with the given probability."""

    return random() < clamp01(chance)


def weighted_choice(weights: Dict[T, float] | Sequence[float], items: Sequence[T] | None = None) -> T:
    """Select an item based on provided ``weights``."""

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
    return items[-1]


def prob_or(probabilities: Sequence[float]) -> float:
    """Return probability that at least one of ``probabilities`` occurs."""

    p = 0.0
    for chance in probabilities:
        p = p + chance - (p * chance)
    return clamp01(p)


def prob_and(probabilities: Sequence[float]) -> float:
    """Return probability that all of ``probabilities`` occur."""

    p = 1.0
    for chance in probabilities:
        p *= chance
    return clamp01(p)


__all__ = ["clamp01", "roll", "weighted_choice", "prob_or", "prob_and"]
