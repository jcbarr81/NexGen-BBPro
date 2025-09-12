"""Batter AI utilities for the play-balance engine.

This module implements simplified batter decision helpers covering strike-zone
handling, pitch identification, swing timing and discipline mechanics.  The
formulas intentionally mirror only a subset of the legacy ``PBINI`` playbalance.  The
configuration object needs to expose the attributes accessed within the
functions below.  Defaults of ``0`` are assumed when attributes are missing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import random

from models.player import Player
from models.pitcher import Pitcher
from .playbalance_config import PlayBalanceConfig
from .probability import clamp01, roll
from .constants import PITCH_RATINGS


# ---------------------------------------------------------------------------
# Strike-zone representation
# ---------------------------------------------------------------------------


@dataclass
class StrikeZoneGrid:
    """Simple rectangular strike-zone grid.

    ``width`` and ``height`` define the number of cells across each axis.  The
    :meth:`zone_at` helper accepts normalised ``x``/``y`` coordinates in the
    ``0.0``–``1.0`` range and returns the corresponding grid cell.  Coordinates
    outside the range are clamped to the nearest edge.
    """

    width: int = 3
    height: int = 3

    def zone_at(self, x: float, y: float) -> tuple[int, int]:
        """Return ``(row, col)`` for a pitch located at ``(x, y)``."""

        # Convert the normalised ``x``/``y`` coordinates into grid indices.
        # ``int`` floors the value which mimics dividing the zone into equal
        # sized rectangles.  ``max``/``min`` clamp out-of-range coordinates.
        col = min(self.width - 1, max(0, int(x * self.width)))
        row = min(self.height - 1, max(0, int(y * self.height)))
        return row, col


# ---------------------------------------------------------------------------
# Look-for logic
# ---------------------------------------------------------------------------


def look_for_zone(
    cfg: PlayBalanceConfig,
    *,
    balls: int,
    strikes: int,
    batter_dis: float,
    grid: StrikeZoneGrid | None = None,
) -> tuple[int, int]:
    """Return strike-zone grid coordinates the batter is focused on.

    The simplified model looks middle for disciplined batters.  When behind in
    the count the target shifts lower in the zone.
    """

    grid = grid or StrikeZoneGrid()
    if batter_dis >= getattr(cfg, "lookForHighDisThresh", 60):
        # Highly disciplined batters look middle regardless of count.
        return grid.zone_at(0.5, 0.5)
    if balls - strikes < 0:
        # Behind in the count the batter protects by looking lower.
        return grid.zone_at(0.5, 0.8)
    # Default is to sit middle-middle.
    return grid.zone_at(0.5, 0.5)


# ---------------------------------------------------------------------------
# Pitch identification
# ---------------------------------------------------------------------------


def pitch_identification_chance(
    cfg: PlayBalanceConfig,
    *,
    batter_pi: float,
    balls: int,
    strikes: int,
) -> float:
    """Return probability that the batter correctly identifies a pitch."""

    base = getattr(cfg, "pitchIdBase", 50) / 100.0
    rating_factor = getattr(cfg, "pitchIdRatingFactor", 0) / 100.0
    count_factor = getattr(cfg, "pitchIdCountFactor", 0) / 100.0
    chance = base
    # Better pitch identification ratings increase success linearly.
    chance += (batter_pi / 100.0) * rating_factor
    # Being ahead in the count affords the batter more selectivity.
    chance += (balls - strikes) * count_factor / 10.0
    return clamp01(chance)


def identify_pitch(cfg: PlayBalanceConfig, **kwargs) -> bool:
    """Return ``True`` when the batter identifies the pitch."""

    return roll(pitch_identification_chance(cfg, **kwargs))


# ---------------------------------------------------------------------------
# Swing timing and adjustments
# ---------------------------------------------------------------------------


def swing_timing(
    cfg: PlayBalanceConfig,
    *,
    batter_sp: float,
    balls: int,
    strikes: int,
) -> float:
    """Return swing timing value in milliseconds."""

    base = getattr(cfg, "swingTimeBase", 0.0)
    count_adj = getattr(cfg, f"swingTime{balls}{strikes}Count", 0.0)
    speed_factor = getattr(cfg, "swingTimeSpeedFactor", 0.0)
    # Faster batters require less time to swing.
    timing = base + count_adj - speed_factor * (batter_sp / 100.0)
    return timing


def adjust_swing_timing(
    cfg: PlayBalanceConfig,
    timing: float,
    *,
    batter_dis: float,
) -> float:
    """Return swing ``timing`` adjusted by discipline."""

    factor = getattr(cfg, "swingAdjustDisciplineFactor", 0.0)
    # Less disciplined batters are late more often; shift timing accordingly.
    return timing + factor * (50.0 - batter_dis) / 100.0


# ---------------------------------------------------------------------------
# Discipline and check-swing
# ---------------------------------------------------------------------------


def discipline_chance(
    cfg: PlayBalanceConfig,
    *,
    batter_dis: float,
    balls: int,
    strikes: int,
) -> float:
    """Return probability the batter lays off a borderline pitch."""

    base = getattr(cfg, "disciplineBase", 50) / 100.0
    rating_factor = getattr(cfg, "disciplineRatingFactor", 0) / 100.0
    ball_factor = getattr(cfg, "disciplineBallFactor", 0) / 100.0
    strike_factor = getattr(cfg, "disciplineStrikeFactor", 0) / 100.0
    chance = base
    # Increase chance to take borderline pitches with higher discipline ratings
    # or when ahead in the count.
    chance += (batter_dis / 100.0) * rating_factor
    chance += balls * ball_factor
    chance -= strikes * strike_factor
    return clamp01(chance)


def check_swing_chance(cfg: PlayBalanceConfig, *, batter_dis: float) -> float:
    """Return probability of successfully checking a swing."""

    base = getattr(cfg, "checkSwingBase", 0) / 100.0
    rating_factor = getattr(cfg, "checkSwingDisFactor", 0) / 100.0
    chance = base + (batter_dis / 100.0) * rating_factor
    return clamp01(chance)


# ---------------------------------------------------------------------------
# Foul-ball and HBP avoidance
# ---------------------------------------------------------------------------


def foul_ball_avoid_chance(
    cfg: PlayBalanceConfig,
    *,
    batter_con: float,
    pitch_quality: float,
) -> float:
    """Return probability of avoiding a foul ball."""

    base = getattr(cfg, "foulBallAvoidBase", 0) / 100.0
    contact_factor = getattr(cfg, "foulBallContactFactor", 0) / 100.0
    quality_factor = getattr(cfg, "foulBallPitchFactor", 0) / 100.0
    chance = base
    chance += (batter_con / 100.0) * contact_factor
    chance -= (pitch_quality / 100.0) * quality_factor
    return clamp01(chance)


def hbp_avoid_chance(cfg: PlayBalanceConfig, *, batter_brav: float) -> float:
    """Return probability the batter avoids a hit-by-pitch."""

    base = getattr(cfg, "hbpAvoidBase", 0) / 100.0
    bravery_factor = getattr(cfg, "hbpAvoidBraveryFactor", 0) / 100.0
    chance = base + (100.0 - batter_brav) / 100.0 * bravery_factor
    return clamp01(chance)


@dataclass
class BatterAI:
    """Very small helper encapsulating batter decision making."""

    config: PlayBalanceConfig
    _primary_cache: Dict[str, str] = None  # type: ignore[assignment]
    _best_cache: Dict[str, str] = None  # type: ignore[assignment]
    last_decision: Tuple[bool, float] | None = None
    last_misread: bool = False

    def _primary_pitch(self, pitcher: Pitcher) -> str:
        if self._primary_cache is None:
            self._primary_cache = {}
        pid = pitcher.player_id
        if pid not in self._primary_cache:
            ratings = {p: getattr(pitcher, p) for p in PITCH_RATINGS}
            primary = max(ratings.items(), key=lambda kv: kv[1])[0]
            self._primary_cache[pid] = primary
        return self._primary_cache[pid]

    def _best_pitch(self, pitcher: Pitcher) -> str:
        if self._best_cache is None:
            self._best_cache = {}
        pid = pitcher.player_id
        if pid not in self._best_cache:
            ratings = {p: getattr(pitcher, p) for p in PITCH_RATINGS}
            best = max(ratings.items(), key=lambda kv: kv[1])[0]
            self._best_cache[pid] = best
        return self._best_cache[pid]

    def pitch_class(self, dist: int) -> str:
        """Return a simple classification for ``dist`` from the zone.

        Distances up to the plate size minus one are treated as "sure" strikes,
        values on the edge are "close" strikes, a small buffer outside the zone
        counts as "close" balls and anything further away is a "sure" ball.
        """

        zone = max(getattr(self.config, "plateWidth", 3), getattr(self.config, "plateHeight", 3))
        if dist <= zone - 1:
            return "sure strike"
        if dist == zone:
            return "close strike"
        if dist <= zone + 2:
            return "close ball"
        return "sure ball"

    def decide_swing(
        self,
        batter: Player,
        pitcher: Pitcher,
        pitch_type: str,
        *,
        balls: int = 0,
        strikes: int = 0,
        look_for: str | None = None,
        dist: int = 0,
        swing_type: str = "normal",
        dx: int | None = None,
        dy: int | None = None,
        random_value: float | None = None,
        check_random: float | None = None,
    ) -> Tuple[bool, float]:
        """Return ``(swing, contact_quality)`` for the pitch.

        Parameters beyond ``balls``, ``strikes`` and ``look_for`` are accepted
        for API compatibility with the legacy implementation.  ``random_value``
        (falling back to :func:`random.random`) determines whether the batter
        swings while ``check_random`` drives the contact check.  Remaining
        values are currently ignored but retained to avoid :class:`TypeError`
        in callers.
        """

        swing = False
        contact_quality = 1.0
        self.last_contact = False

        rv = random.random() if random_value is None else random_value

        pitch_match = False
        if look_for == "primary" and pitch_type == self._primary_pitch(pitcher):
            adj_key = f"lookPrimaryType{balls}{strikes}CountAdjust"
            contact_quality += getattr(self.config, adj_key, 0) / 100.0
            pitch_match = True
        elif look_for == "best" and pitch_type == self._best_pitch(pitcher):
            adj_key = f"lookBestType{balls}{strikes}CountAdjust"
            contact_quality += getattr(self.config, adj_key, 0) / 100.0
            pitch_match = True

        if look_for and not pitch_match:
            contact_quality -= getattr(self.config, "lookMismatchPenalty", 0) / 100.0
            self.last_misread = True
        else:
            self.last_misread = False

        discipline = getattr(batter, "ch", 50) / 100.0
        pitch_kind = self.pitch_class(dist)
        if pitch_kind in {"sure strike", "close strike"}:
            base = 0.66
            swing_chance = base + (discipline - 0.5) * 0.2
        else:
            base = 0.3 if pitch_kind == "close ball" else 0.1
            swing_chance = base - (discipline - 0.5) * 0.2
        swing_chance = clamp01(swing_chance)
        if rv < swing_chance:
            swing = True

        if swing:
            batter_contact = getattr(batter, "ch", 50)
            pitch_quality = getattr(pitcher, pitch_type, getattr(pitcher, "movement", 50))
            miss_chance = (pitch_quality - batter_contact + 50) / 200.0
            miss_chance = max(0.05, min(0.95, miss_chance))
            rv_contact = rv if check_random is None else check_random
            if rv_contact < miss_chance:
                self.last_contact = False
                contact_quality = 0.0
            else:
                self.last_contact = True
        else:
            self.last_contact = False

        self.last_decision = (swing, max(0.0, min(1.0, contact_quality)))
        return self.last_decision


__all__ = [
    "StrikeZoneGrid",
    "look_for_zone",
    "pitch_identification_chance",
    "identify_pitch",
    "swing_timing",
    "adjust_swing_timing",
    "discipline_chance",
    "check_swing_chance",
    "foul_ball_avoid_chance",
    "hbp_avoid_chance",
    "BatterAI",
]
