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

``idRatingEaseScale``
    Multiplier applied to the base identification chance.  Values greater than
    ``1.0`` make pitch recognition easier, reducing misreads and swinging
    strikes.

``adjustUnitsSpeed*``
    Multipliers applied to timing adjustment units when the batter needs to
    speed up or slow down the swing relative to their geared speed.  The
    suffix indicates whether the adjustment is a speed up or slow down and if
    the pitch is above or below the geared speed.

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
    # Whether the last swing completely misread the pitch
    last_misread: bool = False

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

    def _discipline_rating(
        self,
        batter: Player,
        balls: int,
        strikes: int,
        *,
        pitcher_pitches: int = 1,
        scoring_pos: bool = False,
        runner_third_lt_two_outs: bool = False,
        plus_zone: bool = False,
        minus_zone: bool = False,
        next_to_look: bool = False,
        fb_down_middle: bool = False,
    ) -> float:
        """Return the swing discipline rating for ``batter`` in percent.

        The calculation mirrors the PB.INI specification combining ``CH`` and
        ``EXP`` with various count and situational adjustments.  Only a subset of
        situations are exposed as optional keyword arguments to keep the helper
        flexible for tests.  The returned value is clamped to ``0-100``.
        """

        cfg = self.config
        ch = getattr(batter, "ch", 0)
        exp = getattr(batter, "exp", 0)

        base = (
            cfg.get("disciplineRatingBase", 0)
            + ch * cfg.get("disciplineRatingCHPct", 0) / 100.0
            + exp * cfg.get("disciplineRatingExpPct", 0) / 100.0
        )

        adjust = 0.0
        if pitcher_pitches == 0:
            adjust += cfg.get("disciplineRatingNoPitchesAdjust", 0)
        if scoring_pos:
            adjust += cfg.get("disciplineRatingScoringPosAdjust", 0)
        if runner_third_lt_two_outs:
            adjust += cfg.get("disciplineRatingOnThird01OutsAdjust", 0)
        if plus_zone:
            adjust += cfg.get("disciplineRatingPlusZoneAdjust", 0)
        if minus_zone:
            adjust += cfg.get("disciplineRatingMinusZoneAdjust", 0)
        if next_to_look:
            adjust += cfg.get("disciplineRatingLocNextToLookAdjust", 0)
        if fb_down_middle:
            adjust += cfg.get("disciplineRatingFBDownMiddleAdjust", 0)

        adjust += cfg.get(f"disciplineRating{balls}{strikes}CountAdjust", 0)

        rating = (base + adjust) * cfg.get("disciplineRatingPct", 100) / 100.0
        return max(0.0, min(100.0, rating))

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
        *,
        timing_units: int = 0,
        timing_adjust: str | None = None,
    ) -> bool:
        """Return ``True`` if the batter can adjust the swing.

        ``dx`` and ``dy`` are the differences in squares between the batter's
        initial swing location and the actual pitch location.  ``timing_units``
        represents the required swing timing adjustment.  The cost of both
        components is calculated using ``adjustUnitsDiag``,
        ``adjustUnitsHoriz`` and ``adjustUnitsVert`` for location changes and
        the ``adjustUnitsSpeed*`` multipliers for timing adjustments from the
        :class:`~logic.playbalance_config.PlayBalanceConfig`.  Available units
        are based on the batter's ``CH`` rating scaled by ``adjustUnitsCHPct``
        and modified by the swing type specific multipliers.
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

        if timing_units:
            multiplier_key = {
                "speed_up_low": "adjustUnitsSpeedUpLowGeared",
                "speed_up_high": "adjustUnitsSpeedUpHighGeared",
                "slow_down_low": "adjustUnitsSlowDownLowGeared",
                "slow_down_high": "adjustUnitsSlowDownHighGeared",
            }.get(timing_adjust, "")
            mult = cfg.get(multiplier_key, 1) if multiplier_key else 1
            required += timing_units * mult

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
        dx: int = 0,
        dy: int = 0,
        swing_type: str = "normal",
        random_value: float = 0.0,
        check_random: float | None = None,
        timing_units: int = 0,
        timing_adjust: str | None = None,
    ) -> Tuple[bool, float]:
        """Return ``(swing, contact_quality)`` for the next pitch.

        ``random_value`` is expected to be a floating point value in the range
        ``[0.0, 1.0)`` and is typically supplied by the caller to keep the number
        of RNG rolls deterministic for the tests.

        ``dx`` and ``dy`` represent the distance between the batter's intended
        swing location and the actual pitch location.  ``timing_units`` and
        ``timing_adjust`` describe the required timing change relative to the
        batter's geared speed.  When the total adjustment exceeds the batter's
        ability a check-swing roll is performed using the ``checkChanceBase*``
        and ``checkChanceCHPct*`` configuration entries.  ``check_random`` can be
        supplied to deterministically control the outcome of the check-swing
        roll.
        """

        self.last_misread = False
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
        base_percent *= self.config.get("idRatingEaseScale", 1.0)

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
            cfg = self.config
            swing_prob = {
                "sure strike": cfg.get("swingProbSureStrike", 0.75),
                "close strike": cfg.get("swingProbCloseStrike", 0.5),
                "close ball": cfg.get("swingProbCloseBall", 0.35),
                "sure ball": cfg.get("swingProbSureBall", 0.1),
            }[p_class]
            if p_class in {"close ball", "sure ball"}:
                swing_prob = max(
                    0.0, swing_prob - getattr(batter, "ch", 0) / 400.0
                )
            swing_prob *= cfg.get("swingProbScale", 1.0)
            swing_prob = max(0.0, min(1.0, swing_prob))
            swing = rand_type < swing_prob

        if swing and p_class in {"close ball", "sure ball"}:
            disc_roll = (random_value + 0.99) % 1
            rating = self._discipline_rating(batter, balls, strikes)
            if disc_roll < rating / 100.0:
                swing = False

        if not swing:
            contact = 0.0
        else:
            success = int(type_id) + int(loc_id) + int(time_id)
            self.last_misread = success == 0
            if self.last_misread:
                ch = getattr(batter, "ch", 0)
                base_floor = float(self.config.get("minMisreadContact", 0.15))
                scaled_floor = base_floor * ch / 100.0
                contact = max(ch / 1000.0, scaled_floor)
            else:
                ch_factor = getattr(batter, "ch", 0) / 100.0
                weights = [
                    1.0 if ident else ch_factor * 0.5
                    for ident in (type_id, loc_id, time_id)
                ]
                contact = timing_quality * sum(weights) / 3.0

        if swing and not self.can_adjust_swing(
            batter,
            dx,
            dy,
            swing_type=swing_type,
            timing_units=timing_units,
            timing_adjust=timing_adjust,
        ):
            check_rv = (
                (random_value + 0.77) % 1 if check_random is None else check_random
            )
            suffix = swing_type.capitalize()
            base = self.config.get(f"checkChanceBase{suffix}", 0)
            ch_pct = self.config.get(f"checkChanceCHPct{suffix}", 0)
            chance = (
                base + getattr(batter, "ch", 0) * ch_pct / 100.0
            ) / 1000.0
            if check_rv < chance:
                swing = False
                contact = 0.0
            else:
                acc_rv = (check_rv + 0.5) % 1
                if acc_rv < self.config.get("failedCheckContactChance", 0) / 100.0:
                    contact = 0.1
                else:
                    contact = 0.0

        if swing:
            ch = getattr(batter, "ch", 0)
            ch_adj = 1.0 + (
                (ch - 50) / 50.0 * self.config.get("contactAbilityScale", 0.0)
            )
            disc = self._discipline_rating(batter, balls, strikes)
            disc_adj = 1.0 + (
                (disc - 50) / 50.0
            ) * self.config.get("contactDisciplineScale", 0.0)
            contact *= (
                self.config.get("contactQualityScale", 1.0)
                * ch_adj
                * disc_adj
            )
            contact = max(0.0, min(1.0, contact))
            contact += self.config.get("contactProbBoost", 0.0)
            contact = max(0.0, min(1.0, contact))

        self.last_decision = (swing, contact)
        return self.last_decision


__all__ = ["BatterAI"]
