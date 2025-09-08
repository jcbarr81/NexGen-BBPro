"""Simplified physics helpers for the play-balance engine.

Only a handful of calculations are implemented for now.  The goal is to
expose deterministic formulas that unit tests can exercise while the rest of
``PBINI.txt`` is gradually translated.  Functions here accept a
:class:`PlayBalanceConfig` instance but fall back to sensible defaults when
configuration entries are missing.
"""
from __future__ import annotations

from random import Random
from typing import Tuple

from .config import PlayBalanceConfig


def exit_velocity(
    cfg: PlayBalanceConfig,
    power: float,
    *,
    swing_type: str = "normal",
) -> float:
    """Return the exit velocity (mph) for a batted ball.

    The calculation mirrors the simplified logic used in the legacy engine. A
    base velocity is combined with a power based adjustment and finally scaled
    depending on the swing type.
    """

    base = getattr(cfg, "exitVeloBase", 0.0)
    ph_pct = getattr(cfg, "exitVeloPHPct", 0.0)
    speed = base + ph_pct * power / 100.0

    scale = {
        "power": getattr(cfg, "exitVeloPowerPct", 100.0),
        "contact": getattr(cfg, "exitVeloContactPct", 100.0),
        "normal": getattr(cfg, "exitVeloNormalPct", 100.0),
    }.get(swing_type, getattr(cfg, "exitVeloNormalPct", 100.0))

    return speed * scale / 100.0


def pitch_movement(
    cfg: PlayBalanceConfig,
    pitch_type: str,
    *,
    rand: float | None = None,
    rng: Random | None = None,
) -> Tuple[float, float]:
    """Return horizontal and vertical break for ``pitch_type``.

    Break values are derived from configuration entries
    ``{pitch}BreakBaseWidth``/``Height`` and their ``Range`` counterparts.  A
    single random value influences both axes which keeps the number of RNG calls
    predictable for tests.
    """

    rng = rng or Random()
    if rand is None:
        rand = rng.random()

    key = pitch_type.lower()
    base_w = getattr(cfg, f"{key}BreakBaseWidth", 0.0)
    base_h = getattr(cfg, f"{key}BreakBaseHeight", 0.0)
    range_w = getattr(cfg, f"{key}BreakRangeWidth", 0.0)
    range_h = getattr(cfg, f"{key}BreakRangeHeight", 0.0)

    dx = base_w + rand * range_w
    dy = base_h + rand * range_h
    return dx, dy


def pitcher_fatigue(
    cfg: PlayBalanceConfig,
    endurance: int,
    pitches_thrown: int,
) -> Tuple[int, str]:
    """Return remaining pitches and fatigue state for a pitcher.

    ``endurance`` represents the total number of pitches the pitcher can throw
    when fully rested.  As pitches are thrown the remaining count decreases and
    crosses the configured tired/exhausted thresholds.
    """

    remaining = max(0, endurance - pitches_thrown)
    tired = getattr(cfg, "pitcherTiredThresh", 0)
    exhausted = getattr(cfg, "pitcherExhaustedThresh", 0)

    if remaining <= exhausted:
        state = "exhausted"
    elif remaining <= tired:
        state = "tired"
    else:
        state = "fresh"

    return remaining, state


def swing_angle(
    cfg: PlayBalanceConfig,
    gf: int,
    *,
    swing_type: str = "normal",
    pitch_loc: str = "middle",
    rand: float | None = None,
    rng: Random | None = None,
) -> float:
    """Return the swing plane angle in degrees.

    The calculation starts with a base angle which is adjusted by the
    batter's ground/fly tendency and modifiers for swing type and pitch
    location.  A small random component allows callers to supply a seeded
    :class:`Random` instance for deterministic tests.
    """

    base = getattr(cfg, "swingAngleBase", 0.0)
    gf_pct = getattr(cfg, "swingAngleGFPct", 0.0)
    angle = base + gf_pct * gf / 100.0

    angle += {
        "power": getattr(cfg, "swingAnglePowerAdj", 0.0),
        "contact": getattr(cfg, "swingAngleContactAdj", 0.0),
        "normal": 0.0,
    }.get(swing_type, 0.0)

    angle += {
        "inside": getattr(cfg, "swingAngleInsideAdj", 0.0),
        "outside": getattr(cfg, "swingAngleOutsideAdj", 0.0),
        "middle": 0.0,
    }.get(pitch_loc, 0.0)

    rng = rng or Random()
    if rand is None:
        rand = rng.random()
    spread = getattr(cfg, "swingAngleRange", 0.0)
    return angle + (rand - 0.5) * spread


def bat_speed(
    cfg: PlayBalanceConfig,
    ph: int,
    pitch_speed: float,
    *,
    swing_type: str = "normal",
) -> float:
    """Return the swing speed of the bat (mph)."""

    base = getattr(cfg, "batSpeedBase", 0.0)
    ph_pct = getattr(cfg, "batSpeedPHPct", 0.0)
    speed = base + ph_pct * ph / 100.0

    ref_pitch = getattr(cfg, "batSpeedRefPitch", 90.0)
    pitch_pct = getattr(cfg, "batSpeedPitchSpdPct", 0.0)
    speed += (pitch_speed - ref_pitch) * pitch_pct

    scale = {
        "power": getattr(cfg, "batSpeedPowerPct", 100.0),
        "contact": getattr(cfg, "batSpeedContactPct", 100.0),
        "normal": getattr(cfg, "batSpeedNormalPct", 100.0),
    }.get(swing_type, getattr(cfg, "batSpeedNormalPct", 100.0))

    return speed * scale / 100.0


def vertical_hit_angle(
    cfg: PlayBalanceConfig,
    *,
    swing_type: str = "normal",
    rand: float | None = None,
    rng: Random | None = None,
) -> float:
    """Return the vertical launch angle for a batted ball in degrees."""

    base = getattr(cfg, "hitAngleBase", 0.0)
    spread = getattr(cfg, "hitAngleRange", 0.0)
    angle = base

    angle += {
        "power": getattr(cfg, "hitAnglePowerAdj", 0.0),
        "contact": getattr(cfg, "hitAngleContactAdj", 0.0),
        "normal": 0.0,
    }.get(swing_type, 0.0)

    rng = rng or Random()
    if rand is None:
        rand = rng.random()
    return angle + (rand - 0.5) * spread


def ball_roll_distance(
    cfg: PlayBalanceConfig,
    velocity: float,
    *,
    surface: str = "grass",
    altitude: float = 0.0,
    wind_speed: float = 0.0,
) -> float:
    """Return roll distance of a grounded ball in feet."""

    base = velocity * getattr(cfg, "rollSpeedMult", 1.0)
    friction = {
        "grass": getattr(cfg, "rollFrictionGrass", 0.0),
        "turf": getattr(cfg, "rollFrictionTurf", 0.0),
    }.get(surface, getattr(cfg, "rollFrictionGrass", 0.0))
    distance = max(0.0, base - friction)

    alt_pct = getattr(cfg, "rollAltitudePct", 0.0)
    wind_pct = getattr(cfg, "rollWindPct", 0.0)
    distance *= 1 + (altitude * alt_pct + wind_speed * wind_pct) / 100.0
    return distance


def control_miss_effect(
    cfg: PlayBalanceConfig,
    miss_amount: float,
    box: Tuple[float, float],
    pitch_speed: float,
) -> Tuple[Tuple[float, float], float]:
    """Apply control miss effects returning new box dimensions and speed."""

    width, height = box
    inc_pct = getattr(cfg, "controlBoxIncreaseEffCOPct", 0.0)
    increase = miss_amount * inc_pct / 100.0
    new_box = (width + increase, height + increase)

    base_red = getattr(cfg, "speedReductionBase", 0.0)
    eff_pct = getattr(cfg, "speedReductionEffMOPct", 0.0)
    reduction = base_red + miss_amount * eff_pct / 100.0
    return new_box, pitch_speed - reduction


def warm_up_progress(cfg: PlayBalanceConfig, pitches: int) -> float:
    """Return how prepared a pitcher is based on warm-up throws."""

    needed = getattr(cfg, "warmUpPitches", 0)
    if needed <= 0:
        return 1.0
    return min(1.0, pitches / needed)


__all__ = [
    "exit_velocity",
    "pitch_movement",
    "pitcher_fatigue",
    "swing_angle",
    "bat_speed",
    "vertical_hit_angle",
    "ball_roll_distance",
    "control_miss_effect",
    "warm_up_progress",
]
