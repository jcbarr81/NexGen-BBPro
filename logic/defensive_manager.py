from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, Tuple

from .playbalance_config import PlayBalanceConfig


class DefensiveManager:
    """Handle defensive strategy decisions based on PB.INI configuration."""

    def __init__(self, config: PlayBalanceConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()

    @classmethod
    def from_file(
        cls, path: str | Path, rng: random.Random | None = None
    ) -> "DefensiveManager":
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
    # Defensive decisions
    # ------------------------------------------------------------------
    def maybe_charge_bunt(
        self,
        pitcher_fa: int = 0,
        first_fa: int = 0,
        third_fa: int = 0,
        on_first: bool = False,
        on_second: bool = False,
        on_third: bool = False,
    ) -> Tuple[bool, bool]:
        cfg = self.config

        def calc(base: float, fielder_fa: int, situational: float = 0.0) -> bool:
            chance = base + cfg.get("chargeChanceSacChanceAdjust", 0) + situational
            chance += (
                cfg.get("chargeChancePitcherFAPct", 0) * pitcher_fa / 100.0
            )
            chance += cfg.get("chargeChanceFAPct", 0) * fielder_fa / 100.0
            chance *= cfg.get("defManChargeChancePct", 100) / 100.0
            return self._roll(chance)

        first = calc(cfg.get("chargeChanceBaseFirst", 0), first_fa)

        situational = 0.0
        if on_first and on_second:
            situational += cfg.get("chargeChanceThirdOnFirstSecond", 0)
        if on_third:
            situational += cfg.get("chargeChanceThirdOnThird", 0)
        third = calc(cfg.get("chargeChanceBaseThird", 0), third_fa, situational)

        return first, third

    def maybe_hold_runner(self, runner_speed: int) -> bool:
        cfg = self.config
        chance = cfg.get("holdChanceBase", 0)
        if runner_speed >= cfg.get("holdChanceMinRunnerSpeed", 9999):
            chance += cfg.get("holdChanceAdjust", 0)
        return self._roll(chance)

    def maybe_pickoff(
        self, steal_chance: int = 0, lead: int = 0, pitches_since: int = 0
    ) -> bool:
        cfg = self.config
        chance = cfg.get("pickoffChanceBase", 0)
        chance += steal_chance + cfg.get("pickoffChanceStealChanceAdjust", 0)
        chance += cfg.get("pickoffChanceLeadMult", 0) * lead
        chance += cfg.get("pickoffChancePitchesMult", 0) * (
            4 - min(pitches_since, 4)
        )
        return self._roll(chance)

    def maybe_pitch_out(
        self,
        steal_chance: int = 0,
        hit_run_chance: int = 0,
        ball_count: int = 0,
        inning: int = 1,
        is_home_team: bool = False,
    ) -> bool:
        cfg = self.config
        if (
            steal_chance < cfg.get("pitchOutChanceStealThresh", 0)
            and hit_run_chance < cfg.get("pitchOutChanceHitRunThresh", 0)
        ):
            return False
        chance = cfg.get("pitchOutChanceBase", 0)
        if ball_count == 0:
            chance += cfg.get("pitchOutChanceBall0Adjust", 0)
        elif ball_count == 1:
            chance += cfg.get("pitchOutChanceBall1Adjust", 0)
        elif ball_count == 2:
            chance += cfg.get("pitchOutChanceBall2Adjust", 0)
        else:
            chance += cfg.get("pitchOutChanceBall3Adjust", 0)
        if inning == 8:
            chance += cfg.get("pitchOutChanceInn8Adjust", 0)
        elif inning >= 9:
            chance += cfg.get("pitchOutChanceInn9Adjust", 0)
        if is_home_team:
            chance += cfg.get("pitchOutChanceHomeAdjust", 0)
        return self._roll(chance)

    def maybe_pitch_around(
        self,
        inning: int = 1,
        batter_ph: int = 0,
        batter_ch: int = 0,
        on_deck_ph: int = 0,
        on_deck_ch: int = 0,
        batter_gf: int = 50,
        outs: int = 0,
        on_first: bool = False,
        on_second: bool = False,
        on_third: bool = False,
    ) -> Tuple[bool, bool]:
        cfg = self.config
        if inning <= cfg.get("pitchAroundChanceNoInn", 0):
            return False, False

        def level(val: int) -> int:
            if val >= 80:
                return 4
            if val >= 60:
                return 3
            if val >= 40:
                return 2
            if val >= 20:
                return 1
            return 0

        chance = cfg.get("pitchAroundChanceBase", 0)
        if inning in (7, 8):
            chance += cfg.get("pitchAroundChanceInn7Adjust", 0)
        elif inning >= 9:
            chance += cfg.get("pitchAroundChanceInn9Adjust", 0)

        ph_diff = level(batter_ph) - level(on_deck_ph)
        if ph_diff >= 2:
            chance += cfg.get("pitchAroundChancePH2BatAdjust", 0)
        elif ph_diff == 1:
            chance += cfg.get("pitchAroundChancePH1BatAdjust", 0)
        elif ph_diff == 0:
            if batter_ph > on_deck_ph:
                chance += cfg.get("pitchAroundChancePHBatAdjust", 0)
            elif batter_ph < on_deck_ph:
                chance += cfg.get("pitchAroundChancePHODAdjust", 0)
        elif ph_diff == -1:
            chance += cfg.get("pitchAroundChancePH1ODAdjust", 0)
        else:
            chance += cfg.get("pitchAroundChancePH2ODAdjust", 0)

        ch_diff = level(batter_ch) - level(on_deck_ch)
        if ch_diff >= 2:
            chance += cfg.get("pitchAroundChanceCH2BatAdjust", 0)
        elif ch_diff == 1:
            chance += cfg.get("pitchAroundChanceCH1BatAdjust", 0)
        elif ch_diff == 0:
            if batter_ch > on_deck_ch:
                chance += cfg.get("pitchAroundChanceCHBatAdjust", 0)
            elif batter_ch < on_deck_ch:
                chance += cfg.get("pitchAroundChanceCHODAdjust", 0)
        elif ch_diff == -1:
            chance += cfg.get("pitchAroundChanceCH1ODAdjust", 0)
        else:
            chance += cfg.get("pitchAroundChanceCH2ODAdjust", 0)

        if batter_gf < cfg.get("pitchAroundChanceLowGFThresh", 0):
            chance += cfg.get("pitchAroundChanceLowGFAdjust", 0)

        if outs == 0:
            chance += cfg.get("pitchAroundChanceOut0", 0)
        elif outs == 1:
            chance += cfg.get("pitchAroundChanceOut1", 0)
        else:
            chance += cfg.get("pitchAroundChanceOut2", 0)

        if on_second and on_third:
            chance += cfg.get("pitchAroundChanceOn23", 0)

        pitch_around = self._roll(chance)
        ibb = False
        if pitch_around:
            ibb_chance = chance * cfg.get("defManPitchAroundToIBBPct", 0) / 100.0
            ibb = self._roll(ibb_chance)
        return pitch_around, ibb

    # ------------------------------------------------------------------
    # Field positioning
    # ------------------------------------------------------------------
    def _outfield_situation(
        self, situation: str, pull: int = 50, power: int = 50
    ) -> Dict[str, Tuple[float, float]]:
        """Return outfield positions for ``situation``.

        ``situation`` should be one of ``"normal"``, ``"guardLeft"`` or
        ``"guardRight"``.  For ``"normal"`` positions the batter's ``pull`` and
        ``power`` ratings influence the angle and depth respectively.
        """

        cfg = self.config
        positions: Dict[str, Tuple[float, float]] = {}

        depth_mult = cfg.get("outfieldPosPctNormal", 0)
        angle_shift = 0

        if situation == "normal":
            high_pull = cfg.get("defPosHighPull")
            high_pull_extra = cfg.get("defPosHighPullExtra")
            low_pull = cfg.get("defPosLowPull")
            low_pull_extra = cfg.get("defPosLowPullExtra")

            shift_steps = 0
            if high_pull and pull >= high_pull:
                shift_steps = 2
            elif high_pull_extra and pull >= high_pull_extra:
                shift_steps = 1
            elif low_pull and pull <= low_pull:
                shift_steps = -2
            elif low_pull_extra and pull <= low_pull_extra:
                shift_steps = -1

            angle_shift = 5 * shift_steps

            if cfg.get("defPosHighPower") and power >= cfg.get("defPosHighPower"):
                depth_mult = cfg.get("outfieldPosPctDeep", depth_mult)
            elif cfg.get("defPosLowPower") and power <= cfg.get("defPosLowPower"):
                depth_mult = cfg.get("outfieldPosPctShallow", depth_mult)

        for f in ("LF", "CF", "RF"):
            pct_key = f"{situation}Pos{f}Pct"
            angle_key = f"{situation}Pos{f}Angle"
            pct = cfg.get(pct_key)
            angle = cfg.get(angle_key)
            if pct is None or angle is None:
                continue
            dist = pct * depth_mult / 100.0
            positions[f] = (dist, angle + angle_shift)

        return positions

    def set_field_positions(
        self, pull: int = 50, power: int = 50
    ) -> Dict[str, Dict[str, Dict[str, Tuple[float, float]]]]:
        cfg = self.config
        fielders = ["1B", "2B", "SS", "3B"]
        feet_per_depth = cfg.get("infieldPosFeetPerDepth", 0)

        positions: Dict[str, Dict[str, Dict[str, Tuple[float, float]]]] = {
            "infield": {},
            "outfield": {},
        }

        infield_situations = ["normal", "guardLines", "cutoffRun", "doublePlay"]
        for sit in infield_situations:
            sit_dict: Dict[str, Tuple[float, float]] = {}
            for f in fielders:
                dist_key = f"{sit}Pos{f}Dist"
                angle_key = f"{sit}Pos{f}Angle"
                dist = cfg.get(dist_key)
                angle = cfg.get(angle_key)
                if dist is None or angle is None:
                    continue
                feet = dist / 10.0 * feet_per_depth
                sit_dict[f] = (feet, angle)
            if sit_dict:
                positions["infield"][sit] = sit_dict

        positions["outfield"]["normal"] = self._outfield_situation(
            "normal", pull, power
        )
        positions["outfield"]["guardLeft"] = self._outfield_situation("guardLeft")
        positions["outfield"]["guardRight"] = self._outfield_situation("guardRight")

        # Remove empty sections
        if not positions["infield"]:
            del positions["infield"]
        if not positions["outfield"]["normal"]:
            del positions["outfield"]["normal"]
        if not positions["outfield"]["guardLeft"]:
            del positions["outfield"]["guardLeft"]
        if not positions["outfield"]["guardRight"]:
            del positions["outfield"]["guardRight"]
        if not positions["outfield"]:
            del positions["outfield"]

        return positions


__all__ = ["DefensiveManager"]
