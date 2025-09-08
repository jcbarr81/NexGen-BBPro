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


__all__ = ["exit_velocity", "pitch_movement", "pitcher_fatigue"]
