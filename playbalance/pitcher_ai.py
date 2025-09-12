"""Pitcher AI utilities for the play-balance engine.

This module implements a light-weight decision system that mirrors the
structure of the classic ``PBINI`` playbalance.  It provides helpers to vary pitch
ratings, apply situational adjustments, look up pitch objectives for the
current count and ultimately select a pitch type and intended location.

The implementation purposely keeps calculations simple; the real engine will
extend these helpers with the full set of formulas.  For unit tests the
configuration object only needs to expose the attributes accessed within the
functions below.
"""
from __future__ import annotations

from typing import Dict, Mapping, Tuple, List, Set
import random

from models.pitcher import Pitcher
from .playbalance_config import PlayBalanceConfig


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
    # Random number in ``[-pct, pct]`` produces a symmetric spread around the
    # original rating.  The variation is applied multiplicatively and the result
    # is clamped to maintain the ``0-100`` rating scale.
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
    # Merge the two mappings while clamping the result for each pitch type.
    return {
        p: max(0.0, min(100.0, r + adjustments.get(p, 0.0)))
        for p, r in ratings.items()
    }


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
    # Default leaning towards attacking the zone when no entry is configured.
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
        # The first weight bucket exceeding the roll yields the objective.
        if roll <= cumulative:
            objective = obj
            break

    location_map = {"attack": "zone", "chase": "edge", "waste": "ball"}
    location = location_map.get(objective, "zone")
    return pitch, location


class PitcherAI:
    """Very small pitch selection helper used by the legacy simulation."""

    def __init__(self, config: PlayBalanceConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()
        self._established: Dict[str, Set[str]] = {}
        self._primary_cache: Dict[str, str] = {}
        self._variation_cache: Dict[str, Dict[str, int]] = {}
        self.last_selection: Tuple[str, str] | None = None

    def new_game(self) -> None:
        """Reset caches specific to a single game."""

        self._established.clear()
        self._variation_cache.clear()
        self.last_selection = None

    def _primary_pitch(self, pitcher: Pitcher) -> str:
        pid = pitcher.player_id
        if pid not in self._primary_cache:
            ratings = {p: getattr(pitcher, p) for p in _PITCH_RATINGS}
            primary = max(ratings.items(), key=lambda kv: kv[1])[0]
            self._primary_cache[pid] = primary
        return self._primary_cache[pid]

    def select_pitch(self, pitcher: Pitcher, *, balls: int = 0, strikes: int = 0) -> Tuple[str, str]:
        available = {p: getattr(pitcher, p) for p in _PITCH_RATINGS if getattr(pitcher, p) > 0}
        if not available:
            raise ValueError("Pitcher has no available pitch types")

        var_count = self.config.get("pitchRatVariationCount", 0)
        var_faces = self.config.get("pitchRatVariationFaces", 0)
        var_base = self.config.get("pitchRatVariationBase", 0)
        non_establish = self.config.get("nonEstablishedPitchTypeAdjust", 0)
        primary_adjust = self.config.get("primaryPitchTypeAdjust", 0)

        established = self._established.setdefault(pitcher.player_id, set())
        primary = self._primary_pitch(pitcher)

        variations = self._variation_cache.setdefault(pitcher.player_id, {})
        if not variations:
            for name in available:
                offset = 0
                if var_count > 0 and var_faces > 0:
                    offset = var_base
                    for _ in range(var_count):
                        offset += self.rng.randint(1, var_faces)
                variations[name] = offset

        scored: Dict[str, int] = {}
        for name, base_rating in available.items():
            score = base_rating + variations.get(name, 0)
            if name not in established:
                score += non_establish
            if name == primary:
                score += primary_adjust
            scored[name] = score

        pitch_type = max(scored.items(), key=lambda kv: (kv[1], -_PITCH_RATINGS.index(kv[0])))[0]
        established.add(pitch_type)

        prefix = f"pitchObj{balls}{strikes}Count"
        outside_weight = self.config.get(prefix + "OutsideWeight", 0)
        if strikes > balls:
            outside_weight *= 2
        weights = [
            ("establish", self.config.get(prefix + "EstablishWeight", 0)),
            ("outside", outside_weight),
            ("best", self.config.get(prefix + "BestWeight", 0)),
            ("best_center", self.config.get(prefix + "BestCenterWeight", 0)),
            ("fast_center", self.config.get(prefix + "FastCenterWeight", 0)),
            ("plus", self.config.get(prefix + "PlusWeight", 0)),
        ]

        total = sum(weight for _, weight in weights)
        objective = "establish"
        if total > 0:
            roll = self.rng.random() * total
            cumulative = 0
            for obj, weight in weights:
                cumulative += weight
                if roll < cumulative:
                    objective = obj
                    break

        self.last_selection = (pitch_type, objective)
        return self.last_selection


__all__ = [
    "pitch_rating_variation",
    "apply_selection_adjustments",
    "objective_weights_by_count",
    "select_pitch",
    "PitcherAI",
]
