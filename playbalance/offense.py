"""Offensive manager calculations for the play-balance engine."""
from __future__ import annotations

from .config import PlayBalanceConfig
from .probability import clamp01, roll


def steal_chance(
    cfg: PlayBalanceConfig,
    *,
    balls: int,
    strikes: int,
    runner_sp: float,
    pitcher_hold: float,
    pitcher_is_left: bool,
    pitcher_in_windup: bool = False,
    pitcher_is_wild: bool = False,
    outs: int = 0,
    runner_on: int = 1,
    batter_ch: float = 0.0,
    run_diff: int = 0,
) -> float:
    """Return probability that the runner attempts to steal a base.

    The calculation mirrors a subset of the legacy PBINI formulas. Only the
    most influential factors are considered which keeps the function compact yet
    still allows unit tests to reason about monotonic behaviour.
    """

    count_key = f"stealChance{balls}{strikes}Count"
    chance = getattr(cfg, count_key, 0) / 100.0

    # ------------------------------------------------------------------
    # Runner speed
    # ------------------------------------------------------------------
    if runner_sp <= getattr(cfg, "stealChanceVerySlowThresh", 0):
        chance += getattr(cfg, "stealChanceVerySlowAdjust", 0) / 100.0
    elif runner_sp <= getattr(cfg, "stealChanceSlowThresh", 0):
        chance += getattr(cfg, "stealChanceSlowAdjust", 0) / 100.0
    elif runner_sp <= getattr(cfg, "stealChanceMedThresh", 0):
        chance += getattr(cfg, "stealChanceMedAdjust", 0) / 100.0
    elif runner_sp <= getattr(cfg, "stealChanceFastThresh", 0):
        chance += getattr(cfg, "stealChanceFastAdjust", 0) / 100.0
    else:
        chance += getattr(cfg, "stealChanceVeryFastAdjust", 0) / 100.0

    # ------------------------------------------------------------------
    # Pitcher hold ability
    # ------------------------------------------------------------------
    if pitcher_hold <= getattr(cfg, "stealChanceVeryLowHoldThresh", 0):
        chance += getattr(cfg, "stealChanceVeryLowHoldAdjust", 0) / 100.0
    elif pitcher_hold <= getattr(cfg, "stealChanceLowHoldThresh", 0):
        chance += getattr(cfg, "stealChanceLowHoldAdjust", 0) / 100.0
    elif pitcher_hold <= getattr(cfg, "stealChanceMedHoldThresh", 0):
        chance += getattr(cfg, "stealChanceMedHoldAdjust", 0) / 100.0
    elif pitcher_hold <= getattr(cfg, "stealChanceHighHoldThresh", 0):
        chance += getattr(cfg, "stealChanceHighHoldAdjust", 0) / 100.0
    else:
        chance += getattr(cfg, "stealChanceVeryHighHoldAdjust", 0) / 100.0

    # ------------------------------------------------------------------
    # Pitcher traits
    # ------------------------------------------------------------------
    if pitcher_is_left:
        chance += getattr(cfg, "stealChancePitcherFaceAdjust", 0) / 100.0
    else:
        # Right-handed pitchers give runners a better jump.
        chance += getattr(cfg, "stealChancePitcherBackAdjust", 0) / 100.0
    if pitcher_in_windup:
        chance += getattr(cfg, "stealChancePitcherWindupAdjust", 0) / 100.0
    if pitcher_is_wild:
        chance += getattr(cfg, "stealChancePitcherWildAdjust", 0) / 100.0

    # ------------------------------------------------------------------
    # Batter situational modifiers
    # ------------------------------------------------------------------
    if runner_on == 1:
        if outs == 2:
            if batter_ch >= getattr(cfg, "stealChanceOnFirst2OutHighCHThresh", 101):
                chance += getattr(cfg, "stealChanceOnFirst2OutHighCHAdjust", 0) / 100.0
            if batter_ch <= getattr(cfg, "stealChanceOnFirst2OutLowCHThresh", -1):
                chance += getattr(cfg, "stealChanceOnFirst2OutLowCHAdjust", 0) / 100.0
        else:
            if batter_ch >= getattr(cfg, "stealChanceOnFirst01OutHighCHThresh", 101):
                chance += getattr(cfg, "stealChanceOnFirst01OutHighCHAdjust", 0) / 100.0
            if batter_ch <= getattr(cfg, "stealChanceOnFirst01OutLowCHThresh", -1):
                chance += getattr(cfg, "stealChanceOnFirst01OutLowCHAdjust", 0) / 100.0
    elif runner_on == 2:
        if outs == 0:
            chance += getattr(cfg, "stealChanceOnSecond0OutAdjust", 0) / 100.0
        elif outs == 1:
            chance += getattr(cfg, "stealChanceOnSecond1OutAdjust", 0) / 100.0
        else:
            chance += getattr(cfg, "stealChanceOnSecond2OutAdjust", 0) / 100.0
        if batter_ch >= getattr(cfg, "stealChanceOnSecondHighCHThresh", 101):
            chance += getattr(cfg, "stealChanceOnSecondHighCHAdjust", 0) / 100.0

    if run_diff <= getattr(cfg, "stealChanceWayBehindThresh", -999):
        chance += getattr(cfg, "stealChanceWayBehindAdjust", 0) / 100.0

    chance *= getattr(cfg, "offManStealChancePct", 100) / 100.0
    return clamp01(chance)


def maybe_attempt_steal(cfg: PlayBalanceConfig, **kwargs) -> bool:
    """Return ``True`` when a steal should be attempted."""

    return roll(steal_chance(cfg, **kwargs))


def hit_and_run_chance(
    cfg: PlayBalanceConfig,
    *,
    balls: int,
    strikes: int,
    runner_sp: float,
    batter_ch: float,
    batter_ph: float,
    pitcher_wild: float = 50.0,
    run_diff: int = 0,
    runner_on_first: bool = True,
) -> float:
    """Return probability of calling a hit and run."""

    if not runner_on_first:
        return 0.0

    count_key = f"hnrChance{balls}{strikes}Count"
    chance = getattr(cfg, count_key, 0) / 100.0

    if runner_sp >= getattr(cfg, "hnrChanceFastSPThresh", 0):
        chance += getattr(cfg, "hnrChanceFastSPAdjust", 0) / 100.0

    if batter_ch >= getattr(cfg, "hnrChanceHighCHThresh", 0):
        chance += getattr(cfg, "hnrChanceHighCHAdjust", 0) / 100.0

    if batter_ph <= getattr(cfg, "hnrChanceLowPHThresh", 100):
        chance += getattr(cfg, "hnrChanceLowPHAdjust", 0) / 100.0

    if pitcher_wild >= getattr(cfg, "hnrChancePitcherWildThresh", 101):
        chance += getattr(cfg, "hnrChancePitcherWildAdjust", 0) / 100.0

    if run_diff >= getattr(cfg, "hnrChanceAheadThresh", 999):
        chance += getattr(cfg, "hnrChanceAheadAdjust", 0) / 100.0

    chance *= getattr(cfg, "offManHNRChancePct", 100) / 100.0
    return clamp01(chance)


def maybe_hit_and_run(cfg: PlayBalanceConfig, **kwargs) -> bool:
    """Return ``True`` when a hit and run should be attempted."""

    return roll(hit_and_run_chance(cfg, **kwargs))


def sacrifice_bunt_chance(
    cfg: PlayBalanceConfig,
    *,
    batter_ch: float,
    on_deck_ch: float,
    on_deck_ph: float,
    outs: int,
    inning: int,
    run_diff: int,
    runner_on_first: bool,
) -> float:
    """Return probability of a sacrifice bunt."""

    if not runner_on_first:
        return 0.0

    chance = getattr(cfg, "sacChanceBase", 0) / 100.0
    if outs == 1:
        chance += getattr(cfg, "sacChance1OutAdjust", 0) / 100.0

    if inning >= 7 and abs(run_diff) <= 1:
        chance += getattr(cfg, "sacChanceCLAdjust", 0) / 100.0
        if (
            outs == 1
            and on_deck_ch >= getattr(cfg, "sacChanceCL1OutODHighCHThresh", 101)
            and on_deck_ph >= getattr(cfg, "sacChanceCL1OutODHighPHThresh", 101)
        ):
            chance += getattr(cfg, "sacChanceCL1OutODHighAdjust", 0) / 100.0

    chance *= getattr(cfg, "offManSacChancePct", 100) / 100.0
    return clamp01(chance)


def maybe_sacrifice_bunt(cfg: PlayBalanceConfig, **kwargs) -> bool:
    """Return ``True`` when a sacrifice bunt should be attempted."""

    return roll(sacrifice_bunt_chance(cfg, **kwargs))


def squeeze_chance(
    cfg: PlayBalanceConfig,
    *,
    kind: str,
    balls: int,
    strikes: int,
    batter_ch: float,
    batter_ph: float,
    runner_on_third_sp: float,
) -> float:
    """Return probability for a squeeze play.

    ``kind`` may be ``"suicide"`` or ``"safety"`` with the latter having a
    reduced base probability.
    """

    count = balls + strikes
    if count <= 1:
        chance = getattr(cfg, "squeezeChanceLowCountAdjust", 0) / 100.0
    elif count == 2:
        chance = getattr(cfg, "squeezeChanceMedCountAdjust", 0) / 100.0
    else:
        chance = getattr(cfg, "squeezeChanceHighCountAdjust", 0) / 100.0

    if runner_on_third_sp >= getattr(cfg, "squeezeChanceThirdFastSPThresh", 0):
        chance += getattr(cfg, "squeezeChanceThirdFastAdjust", 0) / 100.0

    max_ch = getattr(cfg, "squeezeChanceMaxCH", 100)
    max_ph = getattr(cfg, "squeezeChanceMaxPH", 100)
    chance *= min(batter_ch, max_ch) / max_ch
    chance *= min(batter_ph, max_ph) / max_ph

    chance *= getattr(cfg, "offManSqueezeChancePct", 100) / 100.0

    if kind == "safety":
        chance *= 0.5

    return clamp01(chance)


def maybe_squeeze(cfg: PlayBalanceConfig, *, kind: str, **kwargs) -> bool:
    """Return ``True`` when a squeeze play should be attempted."""

    return roll(squeeze_chance(cfg, kind=kind, **kwargs))


__all__ = [
    "steal_chance",
    "maybe_attempt_steal",
    "hit_and_run_chance",
    "maybe_hit_and_run",
    "sacrifice_bunt_chance",
    "maybe_sacrifice_bunt",
    "squeeze_chance",
    "maybe_squeeze",
]
