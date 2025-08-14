from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from .pbini_loader import load_pbini

# Default values for PlayBalance configuration entries used throughout the
# simplified game logic.  Missing keys will fall back to these values when
# accessed as attributes.  The majority of values default to ``0`` which keeps
# related behaviour disabled unless explicitly enabled by a test case.  A small
# number have different sensible defaults, e.g. ``speedBase`` and
# ``swingSpeedBase`` which mirror the behaviour of the original game engine.
_DEFAULTS: Dict[str, Any] = {
    # Physics --------------------------------------------------------
    "speedBase": 19,
    "speedPct": 5,
    "swingSpeedBase": 61,
    "swingSpeedPHPct": 10,
    "swingSpeedPowerAdjust": 5,
    "swingSpeedNormalAdjust": 0,
    "swingSpeedContactAdjust": -5,
    "swingSpeedBuntAdjust": -70,
    "swingAngleTenthDegreesBase": 44,
    "swingAngleTenthDegreesRange": 0,
    "swingAngleTenthDegreesGFPct": 95,
    "swingAngleTenthDegreesPowerAdjust": 0,
    "swingAngleTenthDegreesContactAdjust": 0,
    "swingAngleTenthDegreesHighAdjust": 20,
    "swingAngleTenthDegreesLowAdjust": -20,
    "swingAngleTenthDegreesOutsideAdjust": 0,
    # Pitcher AI ------------------------------------------------------
    "pitchRatVariationCount": 1,
    "pitchRatVariationFaces": 3,
    "pitchRatVariationBase": -2,
    "nonEstablishedPitchTypeAdjust": 0,
    "primaryPitchTypeAdjust": 50,
    "pitchObj00CountEstablishWeight": 0,
    "pitchObj00CountOutsideWeight": 40,
    "pitchObj00CountBestWeight": 0,
    "pitchObj00CountBestCenterWeight": 0,
    "pitchObj00CountFastCenterWeight": 0,
    "pitchObj00CountPlusWeight": 60,
    # Batter AI -------------------------------------------------------
    "sureStrikeDist": 3,
    "closeStrikeDist": 4,
    "closeBallDist": 5,
    "lookPrimaryType00CountAdjust": 0,
    "lookPrimaryType01CountAdjust": 0,
    "lookPrimaryType02CountAdjust": 0,
    "lookPrimaryType10CountAdjust": 0,
    "lookPrimaryType11CountAdjust": 0,
    "lookPrimaryType12CountAdjust": 0,
    "lookPrimaryType20CountAdjust": 0,
    "lookPrimaryType21CountAdjust": 0,
    "lookPrimaryType22CountAdjust": 0,
    "lookPrimaryType30CountAdjust": 0,
    "lookPrimaryType31CountAdjust": 0,
    "lookPrimaryType32CountAdjust": 0,
    "lookBestType00CountAdjust": 0,
    "lookBestType01CountAdjust": 0,
    "lookBestType02CountAdjust": 0,
    "lookBestType10CountAdjust": 0,
    "lookBestType11CountAdjust": 0,
    "lookBestType12CountAdjust": 0,
    "lookBestType20CountAdjust": 0,
    "lookBestType21CountAdjust": 0,
    "lookBestType22CountAdjust": 0,
    "lookBestType30CountAdjust": 15,
    "lookBestType31CountAdjust": 15,
    "lookBestType32CountAdjust": 0,
    # Offensive manager ----------------------------------------------------
    "offManStealChancePct": 0,
    "stealChanceVerySlowThresh": 0,
    "stealChanceVerySlowAdjust": 0,
    "stealChanceSlowThresh": 0,
    "stealChanceSlowAdjust": 0,
    "stealChanceMedThresh": 0,
    "stealChanceMedAdjust": 0,
    "stealChanceFastThresh": 0,
    "stealChanceFastAdjust": 0,
    "stealChanceVeryFastAdjust": 0,
    "stealChanceVeryLowHoldThresh": 0,
    "stealChanceVeryLowHoldAdjust": 0,
    "stealChanceLowHoldThresh": 0,
    "stealChanceLowHoldAdjust": 0,
    "stealChanceMedHoldThresh": 0,
    "stealChanceMedHoldAdjust": 0,
    "stealChanceHighHoldThresh": 0,
    "stealChanceHighHoldAdjust": 0,
    "stealChanceVeryHighHoldAdjust": 0,
    "stealChancePitcherFaceAdjust": 0,
    "stealChancePitcherBackAdjust": 0,
    "stealChancePitcherWindupAdjust": 0,
    "stealChancePitcherWildAdjust": 0,
    "stealChanceOnFirst2OutHighCHThresh": 0,
    "stealChanceOnFirst2OutHighCHAdjust": 0,
    "stealChanceOnFirst2OutLowCHThresh": 0,
    "stealChanceOnFirst2OutLowCHAdjust": 0,
    "stealChanceOnFirst01OutHighCHThresh": 0,
    "stealChanceOnFirst01OutHighCHAdjust": 0,
    "stealChanceOnFirst01OutLowCHThresh": 0,
    "stealChanceOnFirst01OutLowCHAdjust": 0,
    "stealChanceOnSecond0OutAdjust": 0,
    "stealChanceOnSecond1OutAdjust": 0,
    "stealChanceOnSecond2OutAdjust": 0,
    "stealChanceOnSecondHighCHThresh": 0,
    "stealChanceOnSecondHighCHAdjust": 0,
    "stealChanceWayBehindThresh": 0,
    "stealChanceWayBehindAdjust": 0,
    "hnrChanceBase": 0,
    "hnrChance3MoreBehindAdjust": 0,
    "hnrChance2BehindAdjust": 0,
    "hnrChance1AheadAdjust": 0,
    "hnrChance2MoreAheadAdjust": 0,
    "hnrChanceOn12Adjust": 0,
    "hnrChancePitcherWildAdjust": 0,
    "hnrChance3BallsAdjust": 0,
    "hnrChance2StrikesAdjust": 0,
    "hnrChanceEvenCountAdjust": 0,
    "hnrChance01CountAdjust": 0,
    "hnrChanceSlowSPThresh": 0,
    "hnrChanceSlowSPAdjust": 0,
    "hnrChanceMedSPThresh": 0,
    "hnrChanceMedSPAdjust": 0,
    "hnrChanceFastSPThresh": 0,
    "hnrChanceFastSPAdjust": 0,
    "hnrChanceVeryFastSPAdjust": 0,
    "hnrChanceLowCHThresh": 0,
    "hnrChanceLowCHAdjust": 0,
    "hnrChanceMedCHThresh": 0,
    "hnrChanceMedCHAdjust": 0,
    "hnrChanceHighCHThresh": 0,
    "hnrChanceHighCHAdjust": 0,
    "hnrChanceVeryHighCHAdjust": 0,
    "hnrChanceLowPHThresh": 0,
    "hnrChanceLowPHAdjust": 0,
    "hnrChanceMedPHThresh": 0,
    "hnrChanceMedPHAdjust": 0,
    "hnrChanceHighPHThresh": 0,
    "hnrChanceHighPHAdjust": 0,
    "hnrChanceVeryHighPHAdjust": 0,
    "offManHNRChancePct": 0,
    "sacChanceMaxCH": 1000,
    "sacChanceMaxPH": 1000,
    "sacChanceBase": 0,
    "sacChancePitcherAdjust": 0,
    "sacChance1OutAdjust": 0,
    "sacChanceCLAdjust": 0,
    "sacChanceCL0OutOn12Adjust": 0,
    "sacChanceCLLowCHThresh": 0,
    "sacChanceCLLowPHThresh": 0,
    "sacChanceCLLowCHPHAdjust": 0,
    "sacChancePitcherLowCHThresh": 0,
    "sacChancePitcherLowPHThresh": 0,
    "sacChancePitcherLowCHPHAdjust": 0,
    "offManSacChancePct": 0,
    "squeezeChanceMaxCH": 1000,
    "squeezeChanceMaxPH": 1000,
    "offManSqueezeChancePct": 0,
    "squeezeChanceLowCountAdjust": 0,
    "squeezeChanceMedCountAdjust": 0,
    "squeezeChanceThirdFastSPThresh": 0,
    "squeezeChanceThirdFastAdjust": 0,
    # Defensive manager ----------------------------------------------------
    "chargeChanceBaseThird": 0,
    "chargeChanceSacChanceAdjust": 0,
    "defManChargeChancePct": 0,
    "holdChanceBase": 0,
    "holdChanceMinRunnerSpeed": 0,
    "holdChanceAdjust": 0,
    "pickoffChanceBase": 0,
    "pickoffChanceStealChanceAdjust": 0,
    "pickoffChanceLeadMult": 0,
    "pickoffChancePitchesMult": 0,
    "pitchOutChanceStealThresh": 0,
    "pitchOutChanceHitRunThresh": 0,
    "pitchOutChanceBase": 0,
    "pitchOutChanceBall0Adjust": 0,
    "pitchOutChanceBall1Adjust": 0,
    "pitchOutChanceBall2Adjust": 0,
    "pitchOutChanceBall3Adjust": 0,
    "pitchOutChanceInn8Adjust": 0,
    "pitchOutChanceInn9Adjust": 0,
    "pitchOutChanceHomeAdjust": 0,
    "pitchAroundChanceNoInn": 0,
    "pitchAroundChanceBase": 0,
    "pitchAroundChanceInn7Adjust": 0,
    "pitchAroundChanceInn9Adjust": 0,
    "defManPitchAroundToIBBPct": 0,
    # Substitution manager -------------------------------------------------
    "doubleSwitchPHAdjust": 0,
    "pinchRunChance": 0,
    "defSubChance": 0,
    "doubleSwitchChance": 0,
    "pitcherTiredThresh": 0,
}


@dataclass
class PlayBalanceConfig:
    """Container providing convenient access to ``PlayBalance`` entries.

    The class behaves similarly to a mapping.  Values can be retrieved via the
    :py:meth:`get` method or as attributes.  Missing keys return sensible
    defaults to keep the simulation logic simple and predictable for the unit
    tests.
    """

    values: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayBalanceConfig":
        """Create an instance from a mapping produced by :func:`load_pbini`.

        ``data`` may be either the full nested dictionary returned by
        :func:`load_pbini` or already the ``PlayBalance`` sub-section.
        """

        if "PlayBalance" in data and isinstance(data["PlayBalance"], dict):
            section = data["PlayBalance"]
        else:
            section = data
        # Copy to avoid accidental sharing
        return cls(dict(section))

    @classmethod
    def from_file(cls, path: str | Path) -> "PlayBalanceConfig":
        """Load a PB.INI style file and return the ``PlayBalance`` section."""

        pbini = load_pbini(path)
        return cls.from_dict(pbini)

    # ------------------------------------------------------------------
    # Mapping style helpers
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = 0) -> Any:
        """Return ``key`` from the configuration or ``default`` if missing."""

        return self.values.get(key, default)

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - simple delegation
        return self.values.get(item, _DEFAULTS.get(item, 0))

    def __setattr__(self, key: str, value: Any) -> None:  # pragma: no cover - simple
        if key == "values":
            super().__setattr__(key, value)
        else:
            self.values[key] = value


__all__ = ["PlayBalanceConfig"]
