from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from utils.path_utils import get_base_dir

from .pbini_loader import load_pbini

DATA_DIR = get_base_dir() / "data"
_OVERRIDE_PATH = DATA_DIR / "playbalance_overrides.json"

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
    "averagePitchSpeed": 94,
    "fastPitchBatSlowdownPct": 110,
    "slowPitchBatSpeedupPct": 85,
    "fbSpeedBase": 70,
    "fbSpeedRange": 2,
    "fbSpeedASPct": 30,
    "cbSpeedBase": 55,
    "cbSpeedRange": 2,
    "cbSpeedASPct": 30,
    "cuSpeedBase": 50,
    "cuSpeedRange": 2,
    "cuSpeedASPct": 30,
    "slSpeedBase": 63,
    "slSpeedRange": 2,
    "slSpeedASPct": 30,
    "sbSpeedBase": 55,
    "sbSpeedRange": 2,
    "sbSpeedASPct": 30,
    "kbSpeedBase": 65,
    "kbSpeedRange": 2,
    "kbSpeedASPct": 0,
    "siSpeedBase": 64,
    "siSpeedRange": 2,
    "siSpeedASPct": 30,
    "fbControlBoxWidth": 1,
    "fbControlBoxHeight": 1,
    "cbControlBoxWidth": 1,
    "cbControlBoxHeight": 1,
    "cuControlBoxWidth": 1,
    "cuControlBoxHeight": 1,
    "slControlBoxWidth": 1,
    "slControlBoxHeight": 1,
    "sbControlBoxWidth": 1,
    "sbControlBoxHeight": 1,
    "kbControlBoxWidth": 1,
    "kbControlBoxHeight": 1,
    "siControlBoxWidth": 1,
    "siControlBoxHeight": 1,
    "controlBoxIncreaseEffCOPct": 15,
    "speedReductionBase": 3,
    "speedReductionRange": 3,
    "speedReductionEffMOPct": 5,
    "swingAngleTenthDegreesBase": 44,
    "swingAngleTenthDegreesRange": 0,
    "swingAngleTenthDegreesGFPct": 95,
    "swingAngleTenthDegreesPowerAdjust": 0,
    "swingAngleTenthDegreesContactAdjust": 0,
    "swingAngleTenthDegreesHighAdjust": 20,
    "swingAngleTenthDegreesLowAdjust": -20,
    "swingAngleTenthDegreesOutsideAdjust": 0,
    "rollFrictionGrass": 12,
    "rollFrictionTurf": 10,
    "ballAirResistancePct": 99,
    "ballAltitudePct": 100,
    "ballBaseAltitude": 0,
    "ballTempPct": 33,
    "ballWindSpeedPct": 33,
    "bounceVertTurfPct": 37,
    "bounceHorizTurfPct": 74,
    "bounceVertGrassPct": 35,
    "bounceHorizGrassPct": 72,
    "bounceVertDirtPct": 30,
    "bounceHorizDirtPct": 67,
    "bounceWetAdjust": -3,
    "bounceHotAdjust": 3,
    "bounceColdAdjust": -3,
    "batPowerHandleBase": 35,
    "batPowerHandleRange": 12,
    "batPowerDullBase": 60,
    "batPowerDullRange": 12,
    "batPowerSweetBase": 105,
    "batPowerSweetRange": 15,
    "batPowerEndBase": 60,
    "batPowerEndRange": 12,
    "hitAngleCountPower": 5,
    "hitAngleFacesPower": 13,
    "hitAngleBasePower": -1,
    "hitAngleCountNormal": 5,
    "hitAngleFacesNormal": 13,
    "hitAngleBaseNormal": -1,
    "hitAngleCountContact": 5,
    "hitAngleFacesContact": 13,
    "hitAngleBaseContact": -1,
    "hitAngleCountBunt": 30,
    "hitAngleFacesBunt": 3,
    "hitAngleBaseBunt": -30,
    "maxThrowDistBase": 190,
    "maxThrowDistASPct": 100,
    "throwSpeedIFBase": 52,
    "throwSpeedIFDistPct": 3,
    "throwSpeedIFMax": 92,
    "throwSpeedOFBase": 52,
    "throwSpeedOFDistPct": 3,
    "throwSpeedOFMax": 92,
    # Exit velocity and launch characteristics
    "exitVeloBase": 0,
    "exitVeloPHPct": 0,
    "vertAngleGFPct": 0,
    "sprayAnglePLPct": 0,
    # Hit type distribution reflecting MLB averages
    "hit1BProb": 64,
    "hit2BProb": 20,
    "hit3BProb": 2,
    "hitHRProb": 14,
    # Foul ball tuning -----------------------------------------------
    "foulStrikeBasePct": 30.0,
    "foulContactTrendPct": 1.5,
    "ballInPlayOuts": 1,
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
    "sureStrikeDist": 4,
    "closeStrikeDist": 5,
    "closeBallDist": 4,
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
    # Pitch identification and discipline ---------------------------------
    "idRatingBase": 44,
    "idRatingCHPct": 90,
    "idRatingExpPct": 80,
    "idRatingPitchRatPct": 100,
    "disciplineRatingBase": 0,
    "disciplineRatingCHPct": 150,
    "disciplineRatingExpPct": 100,
    "disciplineRatingPct": 100,
    "disciplineRatingNoPitchesAdjust": 0,
    "disciplineRatingScoringPosAdjust": 0,
    "disciplineRatingOnThird01OutsAdjust": 0,
    "disciplineRatingPlusZoneAdjust": -10,
    "disciplineRatingMinusZoneAdjust": -35,
    "disciplineRatingLocNextToLookAdjust": -10,
    "disciplineRatingFBDownMiddleAdjust": -45,
    "disciplineRating00CountAdjust": 0,
    "disciplineRating01CountAdjust": 30,
    "disciplineRating02CountAdjust": 10,
    "disciplineRating10CountAdjust": -10,
    "disciplineRating11CountAdjust": 10,
    "disciplineRating12CountAdjust": 0,
    "disciplineRating20CountAdjust": -5,
    "disciplineRating21CountAdjust": 5,
    "disciplineRating22CountAdjust": 10,
    "disciplineRating30CountAdjust": 55,
    "disciplineRating31CountAdjust": 0,
    "disciplineRating32CountAdjust": 10,
    # Timing curve thresholds and dice ------------------------------------
    "timingVeryBadThresh": 55,
    "timingVeryBadCount": 7,
    "timingVeryBadFaces": 16,
    "timingVeryBadBase": -59,
    "timingBadThresh": 70,
    "timingBadCount": 7,
    "timingBadFaces": 16,
    "timingBadBase": -59,
    "timingMedThresh": 80,
    "timingMedCount": 7,
    "timingMedFaces": 15,
    "timingMedBase": -56,
    "timingGoodThresh": 86,
    "timingGoodCount": 7,
    "timingGoodFaces": 15,
    "timingGoodBase": -56,
    "timingVeryGoodCount": 9,
    "timingVeryGoodFaces": 13,
    "timingVeryGoodBase": -63,
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
    "longLeadSpeed": 0,
    "pickoffScareSpeed": 0,
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
    "pitchAroundChancePH2BatAdjust": 0,
    "pitchAroundChancePH1BatAdjust": 0,
    "pitchAroundChancePHBatAdjust": 0,
    "pitchAroundChancePHODAdjust": 0,
    "pitchAroundChancePH1ODAdjust": 0,
    "pitchAroundChancePH2ODAdjust": 0,
    "pitchAroundChanceCH2BatAdjust": 0,
    "pitchAroundChanceCH1BatAdjust": 0,
    "pitchAroundChanceCHBatAdjust": 0,
    "pitchAroundChanceCHODAdjust": 0,
    "pitchAroundChanceCH1ODAdjust": 0,
    "pitchAroundChanceCH2ODAdjust": 0,
    "pitchAroundChanceLowGFThresh": 0,
    "pitchAroundChanceLowGFAdjust": 0,
    "pitchAroundChanceOut0": 0,
    "pitchAroundChanceOut1": 0,
    "pitchAroundChanceOut2": 0,
    "pitchAroundChanceOn23": 0,
    "defManPitchAroundToIBBPct": 0,
    # Substitution manager -------------------------------------------------
    "doubleSwitchPHAdjust": 0,
    "doubleSwitchBase": 0,
    "doubleSwitchPitcherDueAdjust": 0,
    "doubleSwitchNoPrimaryPosAdjust": 0,
    "doubleSwitchNoQualifiedPosAdjust": 0,
    "doubleSwitchVeryHighCurrDefThresh": 0,
    "doubleSwitchHighCurrDefThresh": 0,
    "doubleSwitchMedCurrDefThresh": 0,
    "doubleSwitchLowCurrDefThresh": 0,
    "doubleSwitchVeryHighCurrDefAdjust": 0,
    "doubleSwitchHighCurrDefAdjust": 0,
    "doubleSwitchMedCurrDefAdjust": 0,
    "doubleSwitchLowCurrDefAdjust": 0,
    "doubleSwitchVeryLowCurrDefAdjust": 0,
    "doubleSwitchVeryHighNewDefThresh": 0,
    "doubleSwitchHighNewDefThresh": 0,
    "doubleSwitchMedNewDefThresh": 0,
    "doubleSwitchLowNewDefThresh": 0,
    "doubleSwitchVeryHighNewDefAdjust": 0,
    "doubleSwitchHighNewDefAdjust": 0,
    "doubleSwitchMedNewDefAdjust": 0,
    "doubleSwitchLowNewDefAdjust": 0,
    "doubleSwitchVeryLowNewDefAdjust": 0,
    "defSubBase": 0,
    "defSubBeforeInn7Adjust": 0,
    "defSubInn7Adjust": 0,
    "defSubInn8Adjust": 0,
    "defSubAfterInn8Adjust": 0,
    "defSubNoPrimaryPosAdjust": 0,
    "defSubNoQualifiedPosAdjust": 0,
    "defSubPerInjuryPointAdjust": 0,
    "defSubVeryHighCurrDefThresh": 0,
    "defSubHighCurrDefThresh": 0,
    "defSubMedCurrDefThresh": 0,
    "defSubLowCurrDefThresh": 0,
    "defSubVeryHighCurrDefAdjust": 0,
    "defSubHighCurrDefAdjust": 0,
    "defSubMedCurrDefAdjust": 0,
    "defSubLowCurrDefAdjust": 0,
    "defSubVeryLowCurrDefAdjust": 0,
    "defSubVeryHighNewDefThresh": 0,
    "defSubHighNewDefThresh": 0,
    "defSubMedNewDefThresh": 0,
    "defSubLowNewDefThresh": 0,
    "defSubVeryHighNewDefAdjust": 0,
    "defSubHighNewDefAdjust": 0,
    "defSubMedNewDefAdjust": 0,
    "defSubLowNewDefAdjust": 0,
    "defSubVeryLowNewDefAdjust": 0,
    "doubleSwitchChance": 0,
    "warmupPitchCount": 0,
    "warmupSecsPerWarmPitch": 30,
    "warmupSecsPerQuickPitch": 20,
    "warmupSecsPerMaintPitch": 120,
    "warmupSecsPerCoolPitch": 60,
    "warmupSecsBeforeCool": 1800,
    "pitcherTiredThresh": 0,
    # Pitcher substitution thresholds and scoring
    "pitchScoringOut": 0,
    "pitchScoringStrikeOut": 0,
    "pitchScoringOffRun": 0,
    "pitchScoringInnsAfter4": 0,
    "pitchScoringWalk": 0,
    "pitchScoringHit": 0,
    "pitchScoringConsHit": 0,
    "pitchScoringRun": 0,
    "pitchScoringER": 0,
    "pitchScoringHR": 0,
    "pitchScoringWP": 0,
    "starterToastThreshInn1": 0,
    "starterToastThreshInn2": 0,
    "starterToastThreshInn3": 0,
    "starterToastThreshInn4": 0,
    "starterToastThreshInn5": 0,
    "starterToastThreshInn6": 0,
    "starterToastThreshInn7": 0,
    "starterToastThreshInn8": 0,
    "starterToastThreshInn9": 0,
    "starterToastThreshPerInn": 0,
    "starterToastThreshAwayAdjust": 0,
    "starterToastThreshFewBullpenPitchesAdjust": 0,
    "starterToastThreshManyBullpenPitchesAdjust": 0,
    "pitcherExhaustedThresh": 0,
    "tiredPitchRatPct": 100,
    "tiredASPct": 100,
    "exhaustedPitchRatPct": 100,
    "exhaustedASPct": 100,
    "effCOPct": 100,
    "effMOPct": 100,
    "posPlayerPitchingRuns": 0,
    "pitcherToastPctPitchesLeft": 0,
    "pitcherToastMaxLead": 0,
    "pitcherToastMinLead": 0,
    # Pinch running chances and adjustments
    "prChanceOnFirstBase": 0,
    "prChanceOnSecondBase": 0,
    "prChanceOnThirdBase": 0,
    "prChanceWinningRun": 0,
    "prChanceTyingRun": 0,
    "prChanceInsignificant": 0,
    "prChancePerOutAdjust": 0,
    "prChanceEarlyInnAdjust": 0,
    "prChanceMidInnAdjust": 0,
    "prChanceLateInnAdjust": 0,
    "prChanceInn9Adjust": 0,
    "prChanceExtraInnAdjust": 0,
    "prChancePerBenchPlayerAdjust": 0,
    "prChancePerInjuryPointAdjust": 0,
    "prChanceVeryFastSPThresh": 0,
    "prChanceFastSPThresh": 0,
    "prChanceMedSPThresh": 0,
    "prChanceSlowSPThresh": 0,
    "prChanceVeryFastSPAdjust": 0,
    "prChanceFastSPAdjust": 0,
    "prChanceMedSPAdjust": 0,
    "prChanceSlowSPAdjust": 0,
    "prChanceVerySlowSPAdjust": 0,
    "prChanceVeryFastPRThresh": 0,
    "prChanceFastPRThresh": 0,
    "prChanceMedPRThresh": 0,
    "prChanceSlowPRThresh": 0,
    "prChanceVeryFastPRAdjust": 0,
    "prChanceFastPRAdjust": 0,
    "prChanceMedPRAdjust": 0,
    "prChanceSlowPRAdjust": 0,
    "prChanceVerySlowPRAdjust": 0,
    # Fielding AI -------------------------------------------------------
    "couldBeCaughtSlop": -18,
    "shouldBeCaughtSlop": 6,
    "generalSlop": 9,
    "relaySlop": 12,
    "tagTimeSlop": 6,
    "stepOnBagSlop": -5,
    "tagAtBagSlop": 4,
    "throwToBagSlop": 8,
}
_BASE_DEFAULTS = dict(_DEFAULTS)


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
    # Persistence helpers
    # ------------------------------------------------------------------
    @classmethod
    def load_overrides(cls, path: Path | None = None) -> Dict[str, Any]:
        """Merge overrides from ``path`` into the module defaults."""

        path = _OVERRIDE_PATH if path is None else path
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    _DEFAULTS.update(data)
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def save_overrides(self, path: Path | None = None) -> None:
        """Persist current values to ``path`` as overrides."""

        path = _OVERRIDE_PATH if path is None else path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.values, fh, indent=2, sort_keys=True)
        _DEFAULTS.update(self.values)

    def reset(self, path: Path | None = None) -> None:
        """Reset configuration and remove any saved overrides."""

        path = _OVERRIDE_PATH if path is None else path
        self.values.clear()
        _DEFAULTS.clear()
        _DEFAULTS.update(_BASE_DEFAULTS)
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def exit_velo_base(self) -> int:
        """Base exit velocity for batted balls."""
        return int(self.exitVeloBase)

    @property
    def exit_velo_ph_pct(self) -> int:
        """Pinch hitter adjustment percentage for exit velocity."""
        return int(self.exitVeloPHPct)

    @property
    def vert_angle_gf_pct(self) -> int:
        """Ground/fly ratio adjustment for vertical launch angle."""
        return int(self.vertAngleGFPct)

    @property
    def spray_angle_pl_pct(self) -> int:
        """Pull/line percentage for spray angle distribution."""
        return int(self.sprayAnglePLPct)

    # ------------------------------------------------------------------
    # Mapping style helpers
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = 0) -> Any:
        """Return ``key`` from the configuration or ``default`` if missing."""

        return self.values.get(key, default)

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - simple delegation
        values = self.__dict__.get("values", {})
        return values.get(item, _DEFAULTS.get(item, 0))

    def __setattr__(self, key: str, value: Any) -> None:  # pragma: no cover - simple
        if key == "values":
            super().__setattr__(key, value)
        else:
            self.values[key] = value


PlayBalanceConfig.load_overrides()


__all__ = ["PlayBalanceConfig"]
