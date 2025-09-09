"""Pitcher AI utilities for the play-balance engine.

This module implements a light-weight decision system that mirrors the
structure of the classic ``PBINI`` logic.  It provides helpers to vary pitch
ratings, apply situational adjustments, look up pitch objectives for the
current count and ultimately select a pitch type and intended location.

The implementation purposely keeps calculations simple; the real engine will
extend these helpers with the full set of formulas.  For unit tests the
configuration object only needs to expose the attributes accessed within the
functions below.
"""
from __future__ import annotations

from typing import Dict, Mapping, Tuple
import random

from .config import PlayBalanceConfig


# ---------------------------------------------------------------------------
# Rating variation
# ---------------------------------------------------------------------------

def pitch_rating_variation(
    cfg: PlayBalanceConfig,
    rating: float,
    rng: random.Random | None = None,
) -> float:
    """Return ``rating`` with a random variation applied.

    The variation is symmetric around ``rating`` and controlled by the
    ``pitchRatingVariationPct`` configuration attribute (expressed as a
    percentage).  When the configuration attribute is missing, no variation is
    applied.  Results are clamped to the ``0-100`` rating range.
    """

    rng = rng or random
    pct = getattr(cfg, "pitchRatingVariationPct", 0) / 100.0
    if pct <= 0:
        return rating
    # Random number in ``[-pct, pct]``.
    delta = (rng.random() * 2.0 - 1.0) * pct
    return max(0.0, min(100.0, rating * (1.0 + delta)))


# ---------------------------------------------------------------------------
# Selection adjustments
# ---------------------------------------------------------------------------

def apply_selection_adjustments(
    ratings: Mapping[str, float],
    adjustments: Mapping[str, float] | None = None,
) -> Dict[str, float]:
    """Return a new mapping with ``adjustments`` added to ``ratings``.

    ``adjustments`` may provide per-pitch additive modifiers.  Missing entries
    default to ``0``.
    """

    adjustments = adjustments or {}
    return {p: max(0.0, min(100.0, r + adjustments.get(p, 0.0))) for p, r in ratings.items()}


# ---------------------------------------------------------------------------
# Objective weights
# ---------------------------------------------------------------------------

def objective_weights_by_count(
    cfg: PlayBalanceConfig,
    balls: int,
    strikes: int,
) -> Mapping[str, float]:
    """Return pitch objective weights for the given count.

    Configuration provides a ``pitchObjectiveWeights`` attribute mapping count
    strings (``"balls-strikes"``) to objective weight dictionaries.  When the
    count is not present a neutral set of weights is returned where ``attack``
    is favoured.
    """

    table = getattr(cfg, "pitchObjectiveWeights", {})
    key = f"{balls}-{strikes}"
    weights = table.get(key)
    if weights:
        return weights
    return {"attack": 1.0, "chase": 0.5, "waste": 0.0}


# ---------------------------------------------------------------------------
# Decision flow
# ---------------------------------------------------------------------------

def select_pitch(
    cfg: PlayBalanceConfig,
    pitch_ratings: Mapping[str, float],
    balls: int = 0,
    strikes: int = 0,
    rng: random.Random | None = None,
) -> Tuple[str, str]:
    """Return selected pitch type and intended location objective.

    The function applies rating variation and optional per-pitch adjustments,
    then selects the pitch with the highest resulting rating.  An objective is
    chosen based on the configured weights for the count.  The objective is
    mapped to a simple location string (``"zone"``, ``"edge"`` or ``"ball"``).
    """

    rng = rng or random
    # Apply variation and adjustments.
    varied = {p: pitch_rating_variation(cfg, r, rng) for p, r in pitch_ratings.items()}
    adjustments = getattr(cfg, "pitchSelectionAdjust", {})
    adjusted = apply_selection_adjustments(varied, adjustments)

    # Choose pitch with maximum adjusted rating.
    pitch = max(adjusted, key=adjusted.get)

    # Determine objective via weighted randomness using count specific weights.
    weights = objective_weights_by_count(cfg, balls, strikes)
    total = sum(weights.values())
    roll = rng.random() * total if total > 0 else 0.0
    objective = "attack"
    cumulative = 0.0
    for obj, weight in weights.items():
        cumulative += weight
        if roll <= cumulative:
            objective = obj
            break

    location_map = {"attack": "zone", "chase": "edge", "waste": "ball"}
    location = location_map.get(objective, "zone")
    return pitch, location


__all__ = [
    "pitch_rating_variation",
    "apply_selection_adjustments",
    "objective_weights_by_count",
    "select_pitch",
]
