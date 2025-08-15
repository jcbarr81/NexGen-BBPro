import random

from logic.defensive_manager import DefensiveManager
from tests.util.pbini_factory import make_cfg


class MockRandom(random.Random):
    """Deterministic random generator using a predefined sequence."""

    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def random(self):  # type: ignore[override]
        return self.values.pop(0)


def test_charge_bunt_chance():
    cfg = make_cfg(
        chargeChanceBaseFirst=10,
        chargeChanceBaseThird=20,
        chargeChanceSacChanceAdjust=5,
        chargeChancePitcherFAPct=10,
        chargeChanceFAPct=10,
        chargeChanceThirdOnFirstSecond=15,
        chargeChanceThirdOnThird=25,
        defManChargeChancePct=50,
    )
    rng = MockRandom([0.1, 0.3, 0.9, 0.05])
    dm = DefensiveManager(cfg, rng)
    res = dm.maybe_charge_bunt(
        pitcher_fa=40,
        first_fa=30,
        third_fa=60,
        on_first=True,
        on_second=True,
        on_third=False,
    )
    assert res == (True, False)
    res = dm.maybe_charge_bunt(
        pitcher_fa=40,
        first_fa=30,
        third_fa=60,
        on_first=False,
        on_second=False,
        on_third=True,
    )
    assert res == (False, True)


def test_hold_runner_chance():
    cfg = make_cfg(
        holdChanceBase=10,
        holdChanceAdjust=50,
        holdChanceMinRunnerSpeed=30,
    )
    dm = DefensiveManager(cfg, MockRandom([0.5]))
    assert dm.maybe_hold_runner(35) is True  # 60% chance
    dm2 = DefensiveManager(cfg, MockRandom([0.5]))
    assert dm2.maybe_hold_runner(20) is False  # 10% chance


def test_pickoff_chance():
    cfg = make_cfg(
        pickoffChanceBase=10,
        pickoffChanceStealChanceAdjust=10,
        pickoffChanceLeadMult=5,
    )
    rng = MockRandom([0.25, 0.35])
    dm = DefensiveManager(cfg, rng)
    assert dm.maybe_pickoff(steal_chance=5, lead=2) is True
    assert dm.maybe_pickoff(steal_chance=5, lead=2) is False


def test_pitch_out_chance():
    cfg = make_cfg(
        pitchOutChanceStealThresh=10,
        pitchOutChanceBase=20,
        pitchOutChanceBall0Adjust=5,
    )
    rng = MockRandom([0.2, 0.3])
    dm = DefensiveManager(cfg, rng)
    assert dm.maybe_pitch_out(steal_chance=15, ball_count=0) is True
    assert dm.maybe_pitch_out(steal_chance=15, ball_count=0) is False


def test_pitch_around_chance():
    cfg = make_cfg(
        pitchAroundChanceNoInn=0,
        pitchAroundChanceBase=30,
        pitchAroundChanceInn7Adjust=5,
        defManPitchAroundToIBBPct=50,
    )
    rng = MockRandom([0.2, 0.1, 0.4])
    dm = DefensiveManager(cfg, rng)
    pa, ibb = dm.maybe_pitch_around(inning=7)
    assert pa is True and ibb is True
    pa2, ibb2 = dm.maybe_pitch_around(inning=7)
    assert pa2 is False and ibb2 is False
