"""Batter AI utilities for the play-balance engine.

This module implements simplified batter decision helpers covering strike-zone
handling, pitch identification, swing timing and discipline mechanics.  The
formulas intentionally mirror only a subset of the legacy ``PBINI`` logic.  The
configuration object needs to expose the attributes accessed within the
functions below.  Defaults of ``0`` are assumed when attributes are missing.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import PlayBalanceConfig
from .probability import clamp01, roll


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
]
