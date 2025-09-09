
"""Fielder ability calculations for the play-balance engine.

This module implements core formulas controlling how individual fielders
react to batted balls, make catches and throws, and decide whether to chase
balls.  The functions mirror the tuning parameters exposed in ``PBINI.txt``
so unit tests can validate behaviour against the original game's logic.
"""
from __future__ import annotations

from .config import PlayBalanceConfig
from .probability import clamp01

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

POSITION_KEYS = {
    "P": "Pitcher",
    "C": "Catcher",
    "1B": "FirstBase",
    "2B": "SecondBase",
    "3B": "ThirdBase",
    "SS": "ShortStop",
    "LF": "LeftField",
    "CF": "CenterField",
    "RF": "RightField",
}


def _pos_key(position: str) -> str:
    """Return configuration suffix for ``position``."""

    return POSITION_KEYS.get(position, position)


# ---------------------------------------------------------------------------
# Reaction time
# ---------------------------------------------------------------------------

def reaction_delay(cfg: PlayBalanceConfig, position: str, fa: float) -> float:
    """Return the fielder reaction delay in seconds.

    ``fa`` is the fielder's fielding ability rating.  Each position has a base
    delay with a percentage modifier applied to the rating.  Higher fielding
    ability generally reduces the delay (negative percentage).
    """

    fa = max(0.0, fa)
    key = _pos_key(position)
    base = getattr(cfg, f"delayBase{key}", 0.0)
    pct = getattr(cfg, f"delayFAPct{key}", 0.0)
    return max(0.0, base + (pct * fa) / 100.0)


# ---------------------------------------------------------------------------
# Catch probability
# ---------------------------------------------------------------------------

def catch_chance(
    cfg: PlayBalanceConfig,
    position: str,
    fa: float,
    air_time: float,
    distance: float,
    diving: bool = False,
    leaping: bool = False,
) -> float:
    """Return probability that the fielder makes the catch.

    ``air_time`` is the time the ball spends in the air.  ``distance`` is the
    distance from the fielder to the ball when the catch is attempted.  Short
    throws within :attr:`automaticCatchDist` are always caught.
    """

    fa = max(0.0, fa)
    air_time = max(0.0, air_time)
    distance = max(0.0, distance)
    if distance <= getattr(cfg, "automaticCatchDist", 0.0):
        return 1.0

    chance = cfg.catchBaseChance + fa / max(cfg.catchFADiv, 1)
    if diving:
        chance += cfg.catchChanceDiving
    if leaping:
        chance += cfg.catchChanceLeaping
    if air_time < 1.0:
        chance += cfg.catchChanceLessThan1Sec
        tenths = int((1.0 - air_time) * 10)
        chance += tenths * cfg.catchChancePerTenth
    adj_key = f"catchChance{_pos_key(position)}Adjust"
    chance += getattr(cfg, adj_key, 0.0)
    return clamp01(chance / 100.0)


# ---------------------------------------------------------------------------
# Throwing abilities
# ---------------------------------------------------------------------------

def max_throw_distance(cfg: PlayBalanceConfig, arm_strength: float) -> float:
    """Return the maximum throwing distance in feet."""

    arm_strength = max(0.0, arm_strength)
    return cfg.maxThrowDistBase + (cfg.maxThrowDistASPct * arm_strength) / 100.0


def throw_speed(
    cfg: PlayBalanceConfig,
    distance: float,
    arm_strength: float,
    outfielder: bool = False,
) -> float:
    """Return the velocity in mph for a throw to ``distance`` feet."""

    distance = max(0.0, distance)
    arm_strength = max(0.0, arm_strength)
    key = "OF" if outfielder else "IF"
    base = getattr(cfg, f"throwSpeed{key}Base", 0.0)
    dist_pct = getattr(cfg, f"throwSpeed{key}DistPct", 0.0)
    as_pct = getattr(cfg, f"throwSpeed{key}ASPct", 0.0)
    max_speed = getattr(cfg, f"throwSpeed{key}Max", 0.0)
    speed = base + (dist_pct * distance) / 100.0 + (as_pct * arm_strength) / 100.0
    return min(speed, max_speed)


def good_throw_chance(
    cfg: PlayBalanceConfig, position: str, fa: float
) -> float:
    """Return probability of making an accurate throw."""

    fa = max(0.0, fa)
    chance = cfg.goodThrowBase + (cfg.goodThrowFAPct * fa) / 100.0
    adj_key = f"goodThrowChance{_pos_key(position)}"
    chance += getattr(cfg, adj_key, 0.0)
    return clamp01(chance / 100.0)


# ---------------------------------------------------------------------------
# Special catches and chase decisions
# ---------------------------------------------------------------------------

def wild_pitch_catch_chance(
    cfg: PlayBalanceConfig,
    fa: float,
    cross_body: bool = False,
    high: bool = False,
) -> float:
    """Return probability the catcher snags a wild pitch."""

    fa = max(0.0, fa)
    chance = cfg.wildCatchChanceBase + (cfg.wildCatchChanceFAPct * fa) / 100.0
    if cross_body:
        chance += cfg.wildCatchChanceOppMod
    if high:
        chance += cfg.wildCatchChanceHighMod
    return clamp01(chance / 100.0)


def should_chase_ball(cfg: PlayBalanceConfig, position: str, projected_dist: float) -> bool:
    """Return whether the fielder should chase a batted ball.

    ``projected_dist`` represents the distance to the ball when the fielder
    would reach it (for infielders and pitchers) or the distance from home
    plate at the interception point (for outfielders).
    """

    projected_dist = max(0.0, projected_dist)
    if position in {"LF", "CF", "RF"}:
        return projected_dist >= cfg.outfieldMinChaseDist
    if position == "P":
        return projected_dist <= cfg.pitcherMaxChaseDist
    return projected_dist <= cfg.infieldMaxChaseDist


__all__ = [
    "reaction_delay",
    "catch_chance",
    "max_throw_distance",
    "throw_speed",
    "good_throw_chance",
    "wild_pitch_catch_chance",
    "should_chase_ball",
]
