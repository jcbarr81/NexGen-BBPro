"""Generic probability utilities for the play-balance engine."""
from __future__ import annotations

from random import random, randint
from typing import Dict, Sequence, TypeVar

T = TypeVar("T")


def clamp01(value: float) -> float:
    """Clamp ``value`` to the inclusive ``0.0``–``1.0`` range."""
    # ``max`` ensures the lower bound while ``min`` caps the upper bound.
    # The double call avoids branching and keeps the helper extremely small.
    return max(0.0, min(1.0, value))


def roll(chance: float) -> bool:
    """Return ``True`` with the given probability."""
    # Draw a random number in ``0-1`` and compare against the clamped chance.
    # Using ``clamp01`` makes the helper resilient to accidental out-of-range
    # values.
    return random() < clamp01(chance)


def weighted_choice(weights: Dict[T, float] | Sequence[float], items: Sequence[T] | None = None) -> T:
    """Select an item based on provided ``weights``."""
    # Accept either a mapping of item->weight or parallel sequences.  When a
    # mapping is provided we split it into items and weights for simplicity.
    if isinstance(weights, dict):
        items, weights = zip(*weights.items())
    assert items is not None

    # ``total`` defines the size of the cumulative range from which we sample.
    total = sum(weights)
    r = random() * total
    upto = 0.0
    for item, weight in zip(items, weights):
        upto += weight
        # Once the cumulative weight exceeds the roll we found our item.
        if upto >= r:
            return item
    # Fallback in case of floating point rounding handing the last element.
    return items[-1]


def prob_or(probabilities: Sequence[float]) -> float:
    """Return probability that at least one of ``probabilities`` occurs."""
    # We accumulate the combined probability using the inclusion-exclusion
    # principle.  Each additional chance increases the cumulative probability
    # while subtracting the overlap.
    p = 0.0
    for chance in probabilities:
        p = p + chance - (p * chance)
    return clamp01(p)


def prob_and(probabilities: Sequence[float]) -> float:
    """Return probability that all of ``probabilities`` occur."""
    # Start at certainty and successively multiply by each chance which models
    # independent events happening together.
    p = 1.0
    for chance in probabilities:
        p *= chance
    return clamp01(p)


def pct_modifier(chance: float, pct: float) -> float:
    """Apply a percent modifier to ``chance`` as described in ``PBINI``."""
    # Percent modifiers are expressed as whole numbers, e.g. ``5`` means 5%.
    return (pct * chance) / 100.0


def adjustment(chance: float, adjust: float) -> float:
    """Add ``adjust`` to ``chance`` returning the new value."""
    # Simple additive adjustment separated into its own helper for parity with
    # ``pct_modifier`` which mirrors PBINI nomenclature.
    return chance + adjust


def dice_roll(count: int, faces: int, base: int = 0) -> int:
    """Return a roll of ``count`` dice with ``faces`` sides plus ``base``."""
    # Generate ``count`` independent rolls and sum them.  ``base`` is added to
    # allow expressions like ``2d6 + 3`` to be represented.
    return sum(randint(1, faces) for _ in range(count)) + base


def final_chance(base: float, pct_mods: Sequence[float] = (), adjusts: Sequence[float] = ()) -> float:
    """Combine ``base`` chance with percent modifiers and adjustments."""
    # Apply each modifier in order so that percent modifiers affect earlier
    # results and adjustments operate on the already-modified chance.
    chance = base
    for pct in pct_mods:
        chance = pct_modifier(chance, pct)
    for adj in adjusts:
        chance = adjustment(chance, adj)
    return clamp01(chance)


__all__ = [
    "clamp01",
    "roll",
    "weighted_choice",
    "prob_or",
    "prob_and",
    "pct_modifier",
    "adjustment",
    "dice_roll",
    "final_chance",
]
