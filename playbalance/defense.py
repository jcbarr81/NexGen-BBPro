"""Defensive manager calculations for the play-balance engine."""
from __future__ import annotations

from typing import Tuple

from .config import PlayBalanceConfig
from .probability import clamp01


def bunt_charge_chance(
    cfg: PlayBalanceConfig,
    position: str,
    fielder_fa: float,
    pitcher_fa: float,
    sac_chance: float,
    runner_on_first: bool = False,
    runner_on_second: bool = False,
    runner_on_third: bool = False,
) -> float:
    """Return probability that the corner infielder charges a bunt."""

    base_key = "chargeChanceBaseFirst" if position == "1B" else "chargeChanceBaseThird"
    base = getattr(cfg, base_key, 0) / 100.0
    chance = base
    # Factor in the fielding ability of both the pitcher covering and the
    # charging fielder. Values are expressed in percent-of-percent form.
    chance += (cfg.chargeChancePitcherFAPct * pitcher_fa) / 10000.0
    chance += (cfg.chargeChanceFAPct * fielder_fa) / 10000.0
    # Sacrifice likelihood nudges the decision to charge.
    chance += (cfg.chargeChanceSacChanceAdjust + sac_chance) / 100.0
    if position == "3B":
        # Third basemen adjust based on base-state since they have further to go.
        if runner_on_first and runner_on_second:
            chance += cfg.chargeChanceThirdOnFirstSecond / 100.0
        if runner_on_third:
            chance += cfg.chargeChanceThirdOnThird / 100.0
    chance *= cfg.defManChargeChancePct / 100.0
    return clamp01(chance)


def hold_runner_chance(cfg: PlayBalanceConfig, runner_speed: float) -> float:
    """Return probability of holding a runner at first base."""

    chance = cfg.holdChanceBase / 100.0
    if runner_speed >= cfg.holdChanceMinRunnerSpeed:
        # Fast runners entice the defense to hold them on.
        chance += cfg.holdChanceAdjust / 100.0
    return clamp01(chance)


def pickoff_chance(
    cfg: PlayBalanceConfig,
    steal_chance: float,
    lead_level: int,
    pitches_since: int,
) -> float:
    """Return probability of attempting a pickoff on the lead runner."""

    chance = cfg.pickoffChanceBase / 100.0
    chance += (steal_chance + cfg.pickoffChanceStealChanceAdjust) / 100.0
    chance += (lead_level * cfg.pickoffChanceLeadMult) / 100.0
    pitches = max(0, min(pitches_since, 4))
    # The more recent the last pickoff throw, the less likely another occurs.
    chance += (4 - pitches) * cfg.pickoffChancePitchesMult / 100.0
    return clamp01(chance)


def pitch_out_chance(
    cfg: PlayBalanceConfig,
    steal_chance: float,
    hit_run_chance: float,
    balls: int,
    inning: int,
    home_team: bool,
) -> float:
    """Return probability of calling for a pitch out."""

    if (
        steal_chance < cfg.pitchOutChanceStealThresh
        and hit_run_chance < cfg.pitchOutChanceHitRunThresh
    ):
        return 0.0
    chance = cfg.pitchOutChanceBase / 100.0
    ball_adj_key = f"pitchOutChanceBall{balls}Adjust"
    chance += getattr(cfg, ball_adj_key, 0) / 100.0
    if inning == 8:
        chance += cfg.pitchOutChanceInn8Adjust / 100.0
    elif inning >= 9:
        chance += cfg.pitchOutChanceInn9Adjust / 100.0
    if home_team:
        chance += cfg.pitchOutChanceHomeAdjust / 100.0
    return clamp01(chance)


def pitch_around_chance(
    cfg: PlayBalanceConfig,
    inning: int,
    batter_ph: float,
    on_deck_ph: float,
    batter_ch: float,
    on_deck_ch: float,
    ground_fly: float,
    outs: int,
    on_second_and_third: bool,
) -> Tuple[float, float]:
    """Return probabilities of pitching around and issuing an intentional walk."""

    if inning < cfg.pitchAroundChanceNoInn:
        return 0.0, 0.0

    def level(value: float) -> int:
        return min(4, int(value) // 20)

    chance = cfg.pitchAroundChanceBase / 100.0
    if 7 <= inning <= 8:
        chance += cfg.pitchAroundChanceInn7Adjust / 100.0
    elif inning >= 9:
        chance += cfg.pitchAroundChanceInn9Adjust / 100.0

    ph_diff = level(batter_ph) - level(on_deck_ph)
    if ph_diff >= 2:
        chance += cfg.pitchAroundChancePH2BatAdjust / 100.0
    elif ph_diff == 1:
        chance += cfg.pitchAroundChancePH1BatAdjust / 100.0
    elif ph_diff == 0:
        if batter_ph > on_deck_ph:
            chance += cfg.pitchAroundChancePHBatAdjust / 100.0
        elif on_deck_ph > batter_ph:
            chance += cfg.pitchAroundChancePHODAdjust / 100.0
    elif ph_diff == -1:
        chance += cfg.pitchAroundChancePH1ODAdjust / 100.0
    else:
        chance += cfg.pitchAroundChancePH2ODAdjust / 100.0

    ch_diff = level(batter_ch) - level(on_deck_ch)
    if ch_diff >= 2:
        chance += cfg.pitchAroundChanceCH2BatAdjust / 100.0
    elif ch_diff == 1:
        chance += cfg.pitchAroundChanceCH1BatAdjust / 100.0
    elif ch_diff == 0:
        if batter_ch > on_deck_ch:
            chance += cfg.pitchAroundChanceCHBatAdjust / 100.0
        elif on_deck_ch > batter_ch:
            chance += cfg.pitchAroundChanceCHODAdjust / 100.0
    elif ch_diff == -1:
        chance += cfg.pitchAroundChanceCH1ODAdjust / 100.0
    else:
        chance += cfg.pitchAroundChanceCH2ODAdjust / 100.0

    if ground_fly <= cfg.pitchAroundChanceLowGFThresh:
        chance += cfg.pitchAroundChanceLowGFAdjust / 100.0
    if outs == 0:
        chance += cfg.pitchAroundChanceOut0 / 100.0
    elif outs == 1:
        chance += cfg.pitchAroundChanceOut1 / 100.0
    else:
        chance += cfg.pitchAroundChanceOut2 / 100.0
    if on_second_and_third:
        chance += cfg.pitchAroundChanceOn23 / 100.0

    chance = clamp01(chance)
    ibb = clamp01(chance * (cfg.defManPitchAroundToIBBPct / 100.0))
    return chance, ibb


def outfielder_position(
    cfg: PlayBalanceConfig,
    pull_rating: float,
    power_rating: float,
    close_and_late: bool = False,
) -> Tuple[int, str]:
    """Return outfielder shift (-2..2) and depth ('in', 'normal', 'back')."""

    if close_and_late:
        if pull_rating >= cfg.defPosHighPullExtra:
            shift = 1
        elif pull_rating <= cfg.defPosLowPullExtra:
            shift = -1
        else:
            shift = 0
    else:
        if pull_rating >= cfg.defPosHighPull:
            shift = 2
        elif pull_rating >= cfg.defPosHighPullExtra:
            shift = 1
        elif pull_rating <= cfg.defPosLowPull:
            shift = -2
        elif pull_rating <= cfg.defPosLowPullExtra:
            shift = -1
        else:
            shift = 0

    if power_rating >= cfg.defPosHighPower:
        depth = "back"
    elif power_rating <= cfg.defPosLowPower:
        depth = "in"
    else:
        depth = "normal"
    return shift, depth


def fielder_template(
    cfg: PlayBalanceConfig, situation: str, position: str
) -> Tuple[float, float]:
    """Return preset fielder coordinates for a situation and position."""

    dist_key = f"{situation}Pos{position}Dist"
    angle_key = f"{situation}Pos{position}Angle"
    dist = getattr(cfg, dist_key, 0.0)
    angle = getattr(cfg, angle_key, 0.0)
    return float(dist), float(angle)


__all__ = [
    "bunt_charge_chance",
    "hold_runner_chance",
    "pickoff_chance",
    "pitch_out_chance",
    "pitch_around_chance",
    "outfielder_position",
    "fielder_template",
]
