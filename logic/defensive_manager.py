from __future__ import annotations

import random
from pathlib import Path
from typing import Tuple

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

    def maybe_pickoff(self, lead: int = 0, pitches_since: int = 0) -> bool:
        cfg = self.config
        chance = cfg.get("pickoffChanceBase", 0)
        chance += cfg.get("pickoffChanceStealChanceAdjust", 0)
        chance += cfg.get("pickoffChanceLeadMult", 0) * lead
        chance += cfg.get("pickoffChancePitchesMult", 0) * pitches_since
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

    def maybe_pitch_around(self, inning: int = 1) -> Tuple[bool, bool]:
        cfg = self.config
        if inning <= cfg.get("pitchAroundChanceNoInn", 0):
            return False, False
        chance = cfg.get("pitchAroundChanceBase", 0)
        if inning in (7, 8):
            chance += cfg.get("pitchAroundChanceInn7Adjust", 0)
        elif inning >= 9:
            chance += cfg.get("pitchAroundChanceInn9Adjust", 0)
        pitch_around = self._roll(chance)
        ibb = False
        if pitch_around:
            ibb_chance = chance * cfg.get("defManPitchAroundToIBBPct", 0) / 100.0
            ibb = self._roll(ibb_chance)
        return pitch_around, ibb

    # ------------------------------------------------------------------
    # Field positioning
    # ------------------------------------------------------------------
    def set_field_positions(self) -> Dict[str, Dict[str, tuple]]:
        cfg = self.config
        situations = ["normal", "guardLines"]
        fielders = ["1B", "2B", "SS", "3B"]
        positions: Dict[str, Dict[str, tuple]] = {}
        for sit in situations:
            sit_dict: Dict[str, tuple] = {}
            for f in fielders:
                dist_key = f"{sit}Pos{f}Dist"
                angle_key = f"{sit}Pos{f}Angle"
                dist = cfg.get(dist_key)
                angle = cfg.get(angle_key)
                if dist is not None and angle is not None:
                    sit_dict[f] = (dist, angle)
            if sit_dict:
                positions[sit] = sit_dict
        return positions


__all__ = ["DefensiveManager"]
