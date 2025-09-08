"""Generic probability utilities for the play-balance engine."""
from __future__ import annotations

from random import random
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


__all__ = ["roll", "weighted_choice"]
