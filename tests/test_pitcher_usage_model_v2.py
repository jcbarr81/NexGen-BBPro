import pytest
from pathlib import Path

from playbalance.playbalance_config import PlayBalanceConfig
from utils.path_utils import get_base_dir


def _load_cfg() -> PlayBalanceConfig:
    base = get_base_dir()
    return PlayBalanceConfig.from_file(base / "playbalance" / "PBINI.txt")


def test_usage_model_v2_config_defaults_present():
    cfg = _load_cfg()
    # Feature flag
    assert isinstance(cfg.get("enableUsageModelV2", 0), (int, float))
    # Rest curve thresholds
    keys = [
        "restDaysPitchesLvl0",
        "restDaysPitchesLvl1",
        "restDaysPitchesLvl2",
        "restDaysPitchesLvl3",
        "restDaysPitchesLvl4",
        "restDaysPitchesLvl5",
    ]
    vals = [cfg.get(k, None) for k in keys]
    assert all(v is not None for v in vals)
    # Monotonic non-decreasing thresholds
    assert vals == sorted(vals)
    # B2B / consecutive-day rules
    assert cfg.get("b2bMaxPriorPitches", None) is not None
    assert cfg.get("forbidThirdConsecutiveDay", None) is not None
    # Rolling caps by role (3-day/7-day)
    for k in (
        "maxApps3Day_CL",
        "maxApps3Day_SU",
        "maxApps3Day_MR",
        "maxApps3Day_LR",
        "maxApps7Day_CL",
        "maxApps7Day_SU",
        "maxApps7Day_MR",
        "maxApps7Day_LR",
    ):
        assert cfg.get(k, None) is not None
    # Warmup tax present
    assert cfg.get("warmupTaxPitches", None) is not None
    # Pitch budget config keys present
    assert cfg.get("pitchBudgetMultiplier_CL", None) is not None
    assert cfg.get("pitchBudgetRecoveryPct_MR", None) is not None
    assert cfg.get("pitchBudgetAvailThresh_LR", None) is not None
    assert cfg.get("warmupPitchBase_SU", None) is not None
    assert cfg.get("pitchBudgetExhaustionPenaltyScale", None) is not None
    assert cfg.get("starterEarlyOutsThresh", None) is not None
    assert cfg.get("lrBlowoutMargin", None) is not None


@pytest.mark.xfail(reason="UsageModelV2 rest curve not wired yet")
def test_rest_curve_example_mapping():
    """Example expectations for rest-days mapping once implemented.

    These checks lock intended behavior for the new rest curve thresholds.
    When UsageModelV2 wiring is complete, replace this xfail with concrete
    integration checks against the recovery tracker.
    """
    cfg = _load_cfg()
    # Ensure intended default mapping is as documented
    assert cfg.get("restDaysPitchesLvl0") == 10
    assert cfg.get("restDaysPitchesLvl1") == 20
    assert cfg.get("restDaysPitchesLvl2") == 35
    assert cfg.get("restDaysPitchesLvl3") == 50
    assert cfg.get("restDaysPitchesLvl4") == 70
    assert cfg.get("restDaysPitchesLvl5") == 95
