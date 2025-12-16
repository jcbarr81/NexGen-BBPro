from __future__ import annotations

from pathlib import Path

from playbalance.playbalance_config import PlayBalanceConfig
from playbalance.pbini_loader import load_pbini


def make_cfg(**entries: int) -> PlayBalanceConfig:
    """Return a :class:`PlayBalanceConfig` with ``entries`` overridden.

    Tests expect deterministic at-bats, so base hit probabilities default to a
    guaranteed single unless explicitly overridden.  Remaining unspecified keys
    fall back to :class:`PlayBalanceConfig` defaults when accessed.
    """

    base_entries = {
        "hit1BProb": 100,
        "hit2BProb": 0,
        "hit3BProb": 0,
        "hitHRProb": 0,
        "simDeterministicTestMode": 1,
        "enableContactReduction": 0,
        "missChanceScale": 1.0,
        "contactReductionLocked": True,
        "maxHitProb": 1,
        "hitProbCap": 1,
        "swingProbScale": 1.25,
        "zSwingProbScale": 0.79,
        "oSwingProbScale": 0.69,
        "swingProbSureStrike": 0.66,
        "swingProbCloseStrike": 0.46,
        "swingProbCloseBall": 0.56,
        "swingProbSureBall": 0.18,
        "disciplineRatingPct": 0,
        "doublePlayProb": 0,
        "dpHardMinProb": 0,
        "dpForceAutoSec": 5,
        "dpRelayAutoSec": 5,
        "firstToThirdSpeedThreshold": 28,
        "singleFirstToThirdDistance": 210,
        "targetPitchesPerPA": 0,
        "autoTakeCloseBallBaseProb": 0.0,
        "autoTakeSureBallBaseProb": 0.0,
        "autoTakeDistanceWeight": 0.0,
        "autoTakeBallCountWeight": 0.0,
        "autoTakeStrikeCountWeight": 0.0,
        "autoTakeAggressionWeight": 0.0,
        "autoTakeThreeBallBonus": 0.0,
        "autoTakeFullCountBonus": 0.0,
        "autoTakeTwoStrikePenalty": 0.0,
        "autoTakeGlobalMaxProb": 0.0,
        "swingBallDisciplineWeight": 0.0,
        "disciplineZoneProtectWeightDefault": 0.32,
        "disciplineChaseProtectWeightDefault": 0.36,
        "disciplineZoneBiasDefault": 0.16,
        "disciplineChaseBiasDefault": 0.24,
        "contactFactorBase": 1.62,
        "contactFactorDiv": 120,
    }
    base_entries.update(entries)
    cfg = PlayBalanceConfig.from_dict({"PlayBalance": base_entries})
    # Clear pitch objective weights to prevent additional randomness during
    # deterministic unit tests unless explicitly overridden by callers.
    override_keys = set(entries)
    for balls in range(4):
        for strikes in range(3):
            prefix = f"pitchObj{balls}{strikes}Count"
            for suffix in [
                "EstablishWeight",
                "OutsideWeight",
                "BestWeight",
                "BestCenterWeight",
                "FastCenterWeight",
                "PlusWeight",
            ]:
                key = f"{prefix}{suffix}"
                if key not in override_keys:
                    cfg.values[key] = 0
    return cfg


def load_config(path: Path | None = None) -> PlayBalanceConfig:
    """Load the full test configuration from ``path``.

    If ``path`` is ``None`` the default ``playbalance/PBINI.txt`` is used.  This
    helper allows tests to provide their own PlayBalance files when specific
    values need to be exercised.
    """

    path = Path("playbalance/PBINI.txt") if path is None else Path(path)
    pbini = load_pbini(path)
    cfg = PlayBalanceConfig.from_dict(pbini)
    # Default to singles only and deterministic swing probabilities for tests
    cfg.values.update(
        {
            "hit1BProb": 100,
            "hit2BProb": 0,
            "hit3BProb": 0,
            "hitHRProb": 0,
            "simDeterministicTestMode": 1,
            "swingProbSureStrike": 0.66,
            "swingProbCloseStrike": 0.46,
            "swingProbCloseBall": 0.56,
            "swingProbSureBall": 0.18,
            # Keep swing scaling consistent with the vanilla PBINI defaults so
            # engine overrides (e.g. data/playbalance_overrides.json) do not
            # leak into deterministic unit tests.
            "swingProbScale": 1.0,
            "zSwingProbScale": 1.0,
            "oSwingProbScale": 1.0,
            "contactOutcomeScale": 0.92,
            "enableContactReduction": 0,
            "missChanceScale": 1.0,
            "contactReductionLocked": True,
            # Disable auto-take and discipline-side swing penalties for deterministic flows
            "autoTakeCloseBallBaseProb": 0.0,
            "autoTakeSureBallBaseProb": 0.0,
            "autoTakeDistanceWeight": 0.0,
            "autoTakeBallCountWeight": 0.0,
            "autoTakeStrikeCountWeight": 0.0,
            "autoTakeAggressionWeight": 0.0,
            "autoTakeThreeBallBonus": 0.0,
            "autoTakeFullCountBonus": 0.0,
            "autoTakeTwoStrikePenalty": 0.0,
            "autoTakeGlobalMaxProb": 0.0,
            "swingBallDisciplineWeight": 0.0,
            "disciplineZoneProtectWeightDefault": 0.32,
            "disciplineChaseProtectWeightDefault": 0.36,
            "disciplineZoneBiasDefault": 0.16,
            "disciplineChaseBiasDefault": 0.24,
            "contactFactorBase": 1.62,
            "contactFactorDiv": 120,
        }
    )
    # The real configuration contains pitch objective weights which would
    # introduce additional randomness via :class:`PitcherAI`.  Tests expect
    # deterministic behaviour so clear all such weights.
    for balls in range(4):
        for strikes in range(3):
            prefix = f"pitchObj{balls}{strikes}Count"
            for suffix in [
                "EstablishWeight",
                "OutsideWeight",
                "BestWeight",
                "BestCenterWeight",
                "FastCenterWeight",
                "PlusWeight",
            ]:
                cfg.values[f"{prefix}{suffix}"] = 0
    return cfg
