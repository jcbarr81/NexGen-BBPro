from __future__ import annotations

import random
from pathlib import Path

from .playbalance_config import PlayBalanceConfig


class OffensiveManager:
    """Handle offensive strategy decisions based on PB.INI configuration."""

    def __init__(self, config: PlayBalanceConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()

    @classmethod
    def from_file(
        cls, path: str | Path, rng: random.Random | None = None
    ) -> "OffensiveManager":
        cfg = PlayBalanceConfig.from_file(path)
        return cls(cfg, rng)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _roll(self, chance: float) -> bool:
        """Return True with ``chance`` percent probability."""
        chance = max(0.0, min(100.0, chance))
        if chance <= 0:
            return False
        if chance >= 100:
            return True
        return self.rng.random() < chance / 100.0

    # ------------------------------------------------------------------
    # Steal calculations
    # ------------------------------------------------------------------
    def calculate_steal_chance(
        self,
        *,
        balls: int = 0,
        strikes: int = 0,
        runner_sp: int = 0,
        pitcher_hold: int = 0,
        pitcher_is_left: bool = False,
        pitcher_is_wild: bool = False,
        pitcher_in_windup: bool = False,
        outs: int = 0,
        runner_on: int = 1,
        batter_ch: int = 50,
        run_diff: int = 0,
    ) -> float:
        """Return probability that a steal will be attempted."""
        cfg = self.config
        chance = cfg.get("offManStealChancePct", 0)

        count_key = f"stealChance{balls}{strikes}Count"
        chance += cfg.get(count_key, 0)

        sp = runner_sp
        if sp <= cfg.get("stealChanceVerySlowThresh", 0):
            chance += cfg.get("stealChanceVerySlowAdjust", 0)
        elif sp <= cfg.get("stealChanceSlowThresh", 0):
            chance += cfg.get("stealChanceSlowAdjust", 0)
        elif sp <= cfg.get("stealChanceMedThresh", 0):
            chance += cfg.get("stealChanceMedAdjust", 0)
        elif sp <= cfg.get("stealChanceFastThresh", 0):
            chance += cfg.get("stealChanceFastAdjust", 0)
        else:
            chance += cfg.get("stealChanceVeryFastAdjust", 0)

        hold = pitcher_hold
        if hold <= cfg.get("stealChanceVeryLowHoldThresh", 0):
            chance += cfg.get("stealChanceVeryLowHoldAdjust", 0)
        elif hold <= cfg.get("stealChanceLowHoldThresh", 0):
            chance += cfg.get("stealChanceLowHoldAdjust", 0)
        elif hold <= cfg.get("stealChanceMedHoldThresh", 0):
            chance += cfg.get("stealChanceMedHoldAdjust", 0)
        elif hold <= cfg.get("stealChanceHighHoldThresh", 0):
            chance += cfg.get("stealChanceHighHoldAdjust", 0)
        else:
            chance += cfg.get("stealChanceVeryHighHoldAdjust", 0)

        if pitcher_is_left:
            chance += cfg.get("stealChancePitcherFaceAdjust", 0)
        else:
            chance += cfg.get("stealChancePitcherBackAdjust", 0)
        if pitcher_in_windup:
            chance += cfg.get("stealChancePitcherWindupAdjust", 0)
        if pitcher_is_wild:
            chance += cfg.get("stealChancePitcherWildAdjust", 0)

        if runner_on == 1:
            if outs == 2:
                if batter_ch >= cfg.get("stealChanceOnFirst2OutHighCHThresh", 0):
                    chance += cfg.get("stealChanceOnFirst2OutHighCHAdjust", 0)
                if batter_ch <= cfg.get("stealChanceOnFirst2OutLowCHThresh", 0):
                    chance += cfg.get("stealChanceOnFirst2OutLowCHAdjust", 0)
            else:
                if batter_ch >= cfg.get("stealChanceOnFirst01OutHighCHThresh", 0):
                    chance += cfg.get("stealChanceOnFirst01OutHighCHAdjust", 0)
                if batter_ch <= cfg.get("stealChanceOnFirst01OutLowCHThresh", 0):
                    chance += cfg.get("stealChanceOnFirst01OutLowCHAdjust", 0)
        elif runner_on == 2:
            if outs == 0:
                chance += cfg.get("stealChanceOnSecond0OutAdjust", 0)
            elif outs == 1:
                chance += cfg.get("stealChanceOnSecond1OutAdjust", 0)
            else:
                chance += cfg.get("stealChanceOnSecond2OutAdjust", 0)
            if batter_ch >= cfg.get("stealChanceOnSecondHighCHThresh", 0):
                chance += cfg.get("stealChanceOnSecondHighCHAdjust", 0)

        if run_diff <= cfg.get("stealChanceWayBehindThresh", -9999):
            chance += cfg.get("stealChanceWayBehindAdjust", 0)

        chance = max(0.0, min(100.0, chance))
        return chance / 100.0

    # ------------------------------------------------------------------
    # Hit and run
    # ------------------------------------------------------------------
    def calculate_hit_and_run_chance(
        self,
        *,
        runner_sp: int,
        batter_ch: int,
        batter_ph: int,
        balls: int = 0,
        strikes: int = 0,
        run_diff: int = 0,
        runners_on_first_and_second: bool = False,
        pitcher_wild: bool = False,
    ) -> float:
        """Return probability that a hit and run will be attempted."""
        cfg = self.config
        chance = cfg.get("hnrChanceBase", 0)
        if run_diff <= -3:
            chance += cfg.get("hnrChance3MoreBehindAdjust", 0)
        elif run_diff == -2:
            chance += cfg.get("hnrChance2BehindAdjust", 0)
        elif run_diff == 1:
            chance += cfg.get("hnrChance1AheadAdjust", 0)
        elif run_diff >= 2:
            chance += cfg.get("hnrChance2MoreAheadAdjust", 0)

        if runners_on_first_and_second:
            chance += cfg.get("hnrChanceOn12Adjust", 0)
        if pitcher_wild:
            chance += cfg.get("hnrChancePitcherWildAdjust", 0)
        if balls == 3:
            chance += cfg.get("hnrChance3BallsAdjust", 0)
        if strikes == 2:
            chance += cfg.get("hnrChance2StrikesAdjust", 0)
        if balls == strikes:
            chance += cfg.get("hnrChanceEvenCountAdjust", 0)
        if balls == 0 and strikes == 1:
            chance += cfg.get("hnrChance01CountAdjust", 0)

        sp = runner_sp
        if sp <= cfg.get("hnrChanceSlowSPThresh", 0):
            chance += cfg.get("hnrChanceSlowSPAdjust", 0)
        elif sp <= cfg.get("hnrChanceMedSPThresh", 0):
            chance += cfg.get("hnrChanceMedSPAdjust", 0)
        elif sp <= cfg.get("hnrChanceFastSPThresh", 0):
            chance += cfg.get("hnrChanceFastSPAdjust", 0)
        else:
            chance += cfg.get("hnrChanceVeryFastSPAdjust", 0)

        ch = batter_ch
        if ch <= cfg.get("hnrChanceLowCHThresh", 0):
            chance += cfg.get("hnrChanceLowCHAdjust", 0)
        elif ch <= cfg.get("hnrChanceMedCHThresh", 0):
            chance += cfg.get("hnrChanceMedCHAdjust", 0)
        elif ch <= cfg.get("hnrChanceHighCHThresh", 0):
            chance += cfg.get("hnrChanceHighCHAdjust", 0)
        else:
            chance += cfg.get("hnrChanceVeryHighCHAdjust", 0)

        ph = batter_ph
        if ph <= cfg.get("hnrChanceLowPHThresh", 0):
            chance += cfg.get("hnrChanceLowPHAdjust", 0)
        elif ph <= cfg.get("hnrChanceMedPHThresh", 0):
            chance += cfg.get("hnrChanceMedPHAdjust", 0)
        elif ph <= cfg.get("hnrChanceHighPHThresh", 0):
            chance += cfg.get("hnrChanceHighPHAdjust", 0)
        else:
            chance += cfg.get("hnrChanceVeryHighPHAdjust", 0)

        chance *= cfg.get("offManHNRChancePct", 100) / 100.0
        chance = max(0.0, min(100.0, chance))
        return chance / 100.0

    def maybe_hit_and_run(
        self,
        *,
        runner_sp: int,
        batter_ch: int,
        batter_ph: int,
        balls: int = 0,
        strikes: int = 0,
        run_diff: int = 0,
        runners_on_first_and_second: bool = False,
        pitcher_wild: bool = False,
    ) -> bool:
        chance = self.calculate_hit_and_run_chance(
            runner_sp=runner_sp,
            batter_ch=batter_ch,
            batter_ph=batter_ph,
            balls=balls,
            strikes=strikes,
            run_diff=run_diff,
            runners_on_first_and_second=runners_on_first_and_second,
            pitcher_wild=pitcher_wild,
        )
        return self._roll(chance * 100)

    # ------------------------------------------------------------------
    # Sacrifice bunt
    # ------------------------------------------------------------------
    def maybe_sacrifice_bunt(
        self,
        *,
        batter_is_pitcher: bool,
        batter_ch: int,
        batter_ph: int,
        outs: int,
        inning: int,
        on_first: bool,
        on_second: bool,
        run_diff: int,
    ) -> bool:
        cfg = self.config
        if (
            batter_ch > cfg.get("sacChanceMaxCH", 1000)
            or batter_ph > cfg.get("sacChanceMaxPH", 1000)
        ):
            return False

        chance = cfg.get("sacChanceBase", 0)
        if batter_is_pitcher:
            chance += cfg.get("sacChancePitcherAdjust", 0)
        if outs == 1:
            chance += cfg.get("sacChance1OutAdjust", 0)

        close_late = inning >= 7 and -1 <= run_diff <= 1
        if close_late:
            chance += cfg.get("sacChanceCLAdjust", 0)
            if outs == 0 and on_first and on_second:
                chance += cfg.get("sacChanceCL0OutOn12Adjust", 0)
            if (
                batter_ch <= cfg.get("sacChanceCLLowCHThresh", 0)
                and batter_ph <= cfg.get("sacChanceCLLowPHThresh", 0)
            ):
                chance += cfg.get("sacChanceCLLowCHPHAdjust", 0)

        if batter_is_pitcher and (
            batter_ch <= cfg.get("sacChancePitcherLowCHThresh", 0)
            and batter_ph <= cfg.get("sacChancePitcherLowPHThresh", 0)
        ):
            chance += cfg.get("sacChancePitcherLowCHPHAdjust", 0)

        chance *= cfg.get("offManSacChancePct", 100) / 100.0
        return self._roll(chance)

    # ------------------------------------------------------------------
    # Suicide squeeze bunt
    # ------------------------------------------------------------------
    def maybe_suicide_squeeze(
        self,
        *,
        batter_ch: int,
        batter_ph: int,
        balls: int,
        strikes: int,
        runner_on_third_sp: int,
    ) -> bool:
        cfg = self.config
        if (
            batter_ch > cfg.get("squeezeChanceMaxCH", 1000)
            or batter_ph > cfg.get("squeezeChanceMaxPH", 1000)
        ):
            return False

        chance = cfg.get("offManSqueezeChancePct", 0)
        if (balls, strikes) in [(0, 0), (1, 0), (0, 1)]:
            chance += cfg.get("squeezeChanceLowCountAdjust", 0)
        elif (balls, strikes) in [(1, 1), (2, 0)]:
            chance += cfg.get("squeezeChanceMedCountAdjust", 0)

        if runner_on_third_sp >= cfg.get("squeezeChanceThirdFastSPThresh", 0):
            chance += cfg.get("squeezeChanceThirdFastAdjust", 0)

        return self._roll(chance)


__all__ = ["OffensiveManager"]
