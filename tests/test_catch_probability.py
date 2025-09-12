from playbalance.fielding_ai import FieldingAI
from playbalance.playbalance_config import PlayBalanceConfig


def _make_ai():
    cfg = PlayBalanceConfig()
    cfg.catchBaseChance = 90
    cfg.catchFADiv = 7
    cfg.catchChanceDiving = -40
    cfg.catchChanceLeaping = -15
    cfg.catchChanceLessThan1Sec = -10
    cfg.catchChancePerTenth = -1
    cfg.catchChancePitcherAdjust = -10
    cfg.catchChanceCatcherAdjust = 10
    cfg.catchChanceLeftFieldAdjust = 5
    cfg.catchChanceCenterFieldAdjust = 5
    cfg.catchChanceRightFieldAdjust = 5
    cfg.automaticCatchDist = 15
    return FieldingAI(cfg)


def test_diving_and_leaping_affect_probability():
    ai = _make_ai()
    fa = 70
    hang_time = 1.0
    dive = ai.catch_probability("CF", fa, hang_time, "dive")
    leap = ai.catch_probability("CF", fa, hang_time, "leap")
    normal = ai.catch_probability("CF", fa, hang_time, "catch")
    assert normal > leap > dive


def test_position_adjustments_affect_probability():
    ai = _make_ai()
    fa = 70
    hang_time = 1.0
    pitcher = ai.catch_probability("P", fa, hang_time, "catch")
    catcher = ai.catch_probability("C", fa, hang_time, "catch")
    left_field = ai.catch_probability("LF", fa, hang_time, "catch")
    assert catcher > pitcher
    assert left_field > pitcher
