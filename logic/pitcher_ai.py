"""Simplified pitcher AI used by the tests.

The real game contains a fairly involved pitch selection system which takes
into account pitch ratings, how often a pitch has been used and situational
weights for different objectives.  The goal of this module is not to emulate
that behaviour exactly but to provide a small, deterministic subset that
allows tests to verify that configuration values from ``PlayBalance`` are
respected.

Only a handful of options are supported:

``pitchRatVariation*``
    Dice based variation added to the rating of each pitch before a decision is
    made.  Each pitch is rolled separately allowing tests to influence the
    chosen pitch via the RNG sequence.

``nonEstablishedPitchTypeAdjust``
    Adjustment applied to pitches that have not been thrown yet in the current
    game.

``primaryPitchTypeAdjust``
    Adjustment applied to the pitcher's primary pitch which is determined as
    the pitch with the highest base rating.

``pitchObjXXCount*``
    Weights for choosing the objective of a pitch based on the current count
    (balls/strikes).  The objective with the highest weight is selected.  When
    all weights are ``0`` the objective defaults to ``"establish"``.

The class keeps track of which pitch types have been used for each pitcher and
exposes the last chosen ``(pitch_type, objective)`` tuple which is useful in
tests.
"""

from __future__ import annotations

import random
from typing import Dict, List, Set, Tuple

from models.pitcher import Pitcher
from .playbalance_config import PlayBalanceConfig

# Ordering of pitch ratings on the :class:`~models.pitcher.Pitcher` model.  Only
# pitches with a rating greater than ``0`` are considered.
_PITCH_RATINGS: List[str] = ["fb", "sl", "cu", "cb", "si", "scb", "kn"]


class PitcherAI:
    """Very small pitch selection helper used by the tests."""

    def __init__(self, config: PlayBalanceConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()
        # Track which pitches each pitcher has already thrown this game
        self._established: Dict[str, Set[str]] = {}
        # Cache of primary pitch type per pitcher
        self._primary_cache: Dict[str, str] = {}
        self.last_selection: Tuple[str, str] | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _primary_pitch(self, pitcher: Pitcher) -> str:
        """Return the pitch type with the highest base rating."""

        pid = pitcher.player_id
        if pid not in self._primary_cache:
            ratings = {p: getattr(pitcher, p) for p in _PITCH_RATINGS}
            primary = max(ratings.items(), key=lambda kv: kv[1])[0]
            self._primary_cache[pid] = primary
        return self._primary_cache[pid]

    # ------------------------------------------------------------------
    # Pitch selection
    # ------------------------------------------------------------------
    def select_pitch(self, pitcher: Pitcher, *, balls: int = 0, strikes: int = 0) -> Tuple[str, str]:
        """Return ``(pitch_type, objective)`` for the next pitch.

        Only pitch types with a positive rating are considered.  The rating is
        modified by the configuration options described in the module level
        documentation.  The chosen pitch is marked as established for the given
        pitcher.
        """

        available = {
            p: getattr(pitcher, p)
            for p in _PITCH_RATINGS
            if getattr(pitcher, p) > 0
        }
        if not available:
            raise ValueError("Pitcher has no available pitch types")

        var_count = self.config.get("pitchRatVariationCount", 0)
        var_faces = self.config.get("pitchRatVariationFaces", 0)
        var_base = self.config.get("pitchRatVariationBase", 0)
        non_establish = self.config.get("nonEstablishedPitchTypeAdjust", 0)
        primary_adjust = self.config.get("primaryPitchTypeAdjust", 0)

        established = self._established.setdefault(pitcher.player_id, set())
        primary = self._primary_pitch(pitcher)

        scored: Dict[str, int] = {}
        for name, base_rating in available.items():
            score = base_rating
            if var_count > 0 and var_faces > 0:
                score += var_base
                for _ in range(var_count):
                    score += self.rng.randint(1, var_faces)
            if name not in established:
                score += non_establish
            if name == primary:
                score += primary_adjust
            scored[name] = score

        # Choose the pitch with the highest score.  ``max`` is deterministic in
        # case of ties, preserving the order of ``_PITCH_RATINGS``.
        pitch_type = max(scored.items(), key=lambda kv: (kv[1], -_PITCH_RATINGS.index(kv[0])))[0]
        established.add(pitch_type)

        # Determine the pitch objective based on count specific weights
        prefix = f"pitchObj{balls}{strikes}Count"
        weights = {
            "establish": self.config.get(prefix + "EstablishWeight", 0),
            "outside": self.config.get(prefix + "OutsideWeight", 0),
            "best": self.config.get(prefix + "BestWeight", 0),
            "best_center": self.config.get(prefix + "BestCenterWeight", 0),
            "fast_center": self.config.get(prefix + "FastCenterWeight", 0),
            "plus": self.config.get(prefix + "PlusWeight", 0),
        }
        objective = "establish"
        max_weight = weights[objective]
        for obj, weight in weights.items():
            if weight > max_weight:
                objective = obj
                max_weight = weight

        self.last_selection = (pitch_type, objective)
        return self.last_selection


__all__ = ["PitcherAI"]

