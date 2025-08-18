"""Simplified batter AI used by the tests.

The real engine contains a complex batter decision system considering pitch
location, pitch type recognition and count specific adjustments.  The goal of
this module is not to reproduce that behaviour exactly but to expose a minimal
subset that allows unit tests to verify that values from :class:`PlayBalance`
configuration influence swing decisions and contact quality.

Only a handful of options are supported:

``sureStrikeDist``
    Distance from the centre of the strike zone that is considered a guaranteed
    strike.  The simulation currently assumes all pitches have a distance of
    ``0`` but the value still influences strike detection when calling the AI
    directly in tests.

``lookPrimaryTypeXXCountAdjust``
    Count specific adjustment applied when the batter is looking for the
    pitcher's primary pitch.  ``XX`` represents the current ``balls`` and
    ``strikes`` count.  When the pitched type matches and the batter is looking
    for the primary pitch the adjustment increases the chance to correctly
    identify the pitch.

``lookBestTypeXXCountAdjust``
    Count specific adjustment applied when the batter is looking for the
    pitcher's best (highest rated) pitch. ``XX`` represents the current
    ``balls`` and ``strikes`` count. When the pitched type matches the
    pitcher's best pitch the adjustment increases the chance to correctly
    identify the pitch.

``idRatingBase``
    Base chance in percent to correctly identify the pitch type.  Higher values
    improve both swing decisions and contact quality.

The :class:`BatterAI` exposes :func:`decide_swing` which returns a tuple of
``(swing, contact_quality)``.  ``swing`` determines whether the batter offers at
        the pitch.  ``contact_quality`` is a multiplier in the range ``0.0`` to
``1.0`` that represents the quality of the swing timing.  Tests and the game
loop can use this value to influence hit probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import random

from models.player import Player
from models.pitcher import Pitcher
from .playbalance_config import PlayBalanceConfig

# Ordering of pitch ratings on the :class:`~models.pitcher.Pitcher` model.  This
# mirrors the constant used by :mod:`logic.pitcher_ai` but is duplicated here to
# keep the modules independent.
_PITCH_RATINGS = ["fb", "sl", "cu", "cb", "si", "scb", "kn"]


@dataclass
class BatterAI:
    """Very small helper encapsulating batter decision making."""

    config: PlayBalanceConfig

    # Cache of primary pitch type per pitcher
    _primary_cache: Dict[str, str] = None  # type: ignore[assignment]
    # Cache of best pitch (highest rated) per pitcher
    _best_cache: Dict[str, str] = None  # type: ignore[assignment]

    # Last ``(swing, contact_quality)`` decision made.  Useful for tests.
    last_decision: Tuple[bool, float] | None = None

    def __post_init__(self) -> None:  # pragma: no cover - simple initialiser
        if self._primary_cache is None:
            self._primary_cache = {}
        if self._best_cache is None:
            self._best_cache = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _primary_pitch(self, pitcher: Pitcher) -> str:
        pid = pitcher.player_id
        if pid not in self._primary_cache:
            ratings = {p: getattr(pitcher, p) for p in _PITCH_RATINGS}
            primary = max(ratings.items(), key=lambda kv: kv[1])[0]
            self._primary_cache[pid] = primary
        return self._primary_cache[pid]

    def _best_pitch(self, pitcher: Pitcher) -> str:
        pid = pitcher.player_id
        if pid not in self._best_cache:
            ratings = {p: getattr(pitcher, p) for p in _PITCH_RATINGS}
            best = max(ratings.items(), key=lambda kv: kv[1])[0]
            self._best_cache[pid] = best
        return self._best_cache[pid]

    # ------------------------------------------------------------------
    # Decision making
    # ------------------------------------------------------------------
    def pitch_class(self, dist: int) -> str:
        """Return pitch classification based on distance from the zone centre."""

        sure_strike = self.config.get("sureStrikeDist", 3)
        close_strike = self.config.get("closeStrikeDist", sure_strike + 1)
        close_ball = self.config.get("closeBallDist", close_strike + 1)

        if dist <= sure_strike:
            return "sure strike"
        if dist <= close_strike:
            return "close strike"
        if dist <= close_ball:
            return "close ball"
        return "sure ball"

    def can_adjust_swing(
        self,
        batter: Player,
        dx: int,
        dy: int,
        swing_type: str = "normal",
    ) -> bool:
        """Return ``True`` if the batter can adjust the swing location.

        ``dx`` and ``dy`` are the difference in squares between the batter's
        initial swing location and the actual pitch location.  The cost of the
        adjustment is calculated using ``adjustUnitsDiag``,
        ``adjustUnitsHoriz`` and ``adjustUnitsVert`` from the
        :class:`~logic.playbalance_config.PlayBalanceConfig`.  Available units
        are based on the batter's ``CH`` rating scaled by
        ``adjustUnitsCHPct`` and modified by the swing type specific
        multipliers.
        """

        cfg = self.config
        ch = getattr(batter, "ch", 0)
        units = ch * cfg.get("adjustUnitsCHPct", 0) / 100.0
        units *= {
            "power": cfg.get("adjustUnitsPowerPct", 100) / 100.0,
            "contact": cfg.get("adjustUnitsContactPct", 100) / 100.0,
        }.get(swing_type, 1.0)

        diag = min(abs(dx), abs(dy))
        horiz = abs(dx) - diag
        vert = abs(dy) - diag
        required = (
            diag * cfg.get("adjustUnitsDiag", 0)
            + horiz * cfg.get("adjustUnitsHoriz", 0)
            + vert * cfg.get("adjustUnitsVert", 0)
        )

        return units >= required

    # ------------------------------------------------------------------
    # Main decision method
    # ------------------------------------------------------------------
    def decide_swing(
        self,
        batter: Player,
        pitcher: Pitcher,
        *,
        pitch_type: str,
        balls: int = 0,
        strikes: int = 0,
        dist: int = 0,
        random_value: float = 0.0,
    ) -> Tuple[bool, float]:
        """Return ``(swing, contact_quality)`` for the next pitch.

        ``random_value`` is expected to be a floating point value in the range
        ``[0.0, 1.0)`` and is typically supplied by the caller to keep the number
        of RNG rolls deterministic for the tests.
        """

        p_class = self.pitch_class(dist)
        is_strike = p_class in {"sure strike", "close strike"}

        # ------------------------------------------------------------------
        # Identification chances
        # ------------------------------------------------------------------
        # Base identification chance taking batter ratings and pitch quality
        # into account.  The real engine uses a formula documented in
        # ``PBINI.txt`` which combines the batter's CH (contact) and EXP
        # (experience) ratings with the difficulty of the pitch.
        ch_pct = self.config.get("idRatingCHPct", 100) / 100.0
        exp_pct = self.config.get("idRatingExpPct", 100) / 100.0
        pitch_pct = self.config.get("idRatingPitchRatPct", 100) / 100.0

        batter_ch = getattr(batter, "ch", 0)
        batter_exp = getattr(batter, "exp", 0)
        pitch_rating = getattr(pitcher, pitch_type, 50)

        base_percent = (
            self.config.get("idRatingBase", 0)
            + batter_ch * ch_pct
            + batter_exp * exp_pct
            + (100 - pitch_rating) / 2.0 * pitch_pct
        )

        # Choose timing curve based on base identification chance
        curves = [
            ("VeryBad", self.config.get("timingVeryBadThresh", 0)),
            ("Bad", self.config.get("timingBadThresh", 0)),
            ("Med", self.config.get("timingMedThresh", 0)),
            ("Good", self.config.get("timingGoodThresh", 0)),
            ("VeryGood", 101),
        ]
        curve = "VeryGood"
        for name, thresh in curves:
            if base_percent < thresh:
                curve = name
                break
        count = getattr(self.config, f"timing{curve}Count", 0)
        faces = getattr(self.config, f"timing{curve}Faces", 0)
        base_roll = getattr(self.config, f"timing{curve}Base", 0)
        rng = random.Random(random_value)
        timing_offset = base_roll
        for _ in range(max(0, count)):
            timing_offset += rng.randint(1, max(1, faces))
        timing_quality = max(0.0, 1.0 - abs(timing_offset) / 100.0)

        # Weighting for the three recognition components
        type_percent = (
            base_percent * self.config.get("idRatingTypeWeight", 100) / 100.0
        )
        loc_percent = (
            base_percent * self.config.get("idRatingLocWeight", 100) / 100.0
        )
        time_percent = (
            base_percent * self.config.get("idRatingTimingWeight", 100) / 100.0
        )

        # Count based adjustments only apply to type identification
        primary = self._primary_pitch(pitcher)
        best = self._best_pitch(pitcher)
        look_primary_key = f"lookPrimaryType{balls}{strikes}CountAdjust"
        look_best_key = f"lookBestType{balls}{strikes}CountAdjust"
        if pitch_type == primary:
            type_percent += self.config.get(look_primary_key, 0)
        if pitch_type == best:
            type_percent += self.config.get(look_best_key, 0)

        # Convert to probabilities in the range [0.0, 1.0]
        clamp = lambda v: max(0.0, min(1.0, v / 100.0))
        type_chance = clamp(type_percent)
        loc_chance = clamp(loc_percent)
        time_chance = clamp(time_percent)

        # Derive three deterministic random values from the single supplied
        # ``random_value``.  This keeps the method signature simple while still
        # providing independent rolls for type, location and timing checks.
        rand_type = random_value
        rand_loc = (random_value + 0.33) % 1
        rand_time = (random_value + 0.66) % 1

        type_id = rand_type < type_chance
        loc_id = rand_loc < loc_chance
        time_id = rand_time < time_chance

        if type_id or loc_id:
            swing = is_strike
        else:
            swing_probs = {
                "sure strike": 0.75,
                "close strike": 0.5,
                "close ball": 0.25,
                "sure ball": 0.0,
            }
            swing = rand_type < swing_probs[p_class]

        contact = (
            timing_quality
            if swing and type_id and time_id
            else 0.5 if swing else 0.0
        )
        self.last_decision = (swing, contact)
        return self.last_decision


__all__ = ["BatterAI"]
