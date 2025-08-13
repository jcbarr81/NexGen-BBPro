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
        chargeChanceBaseThird=20,
        chargeChanceSacChanceAdjust=10,
        defManChargeChancePct=50,
    )
    rng = MockRandom([0.1, 0.2])
    dm = DefensiveManager(cfg, rng)
    assert dm.maybe_charge_bunt() is True
    assert dm.maybe_charge_bunt() is False


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
    assert dm.maybe_pickoff(lead=2) is True
    assert dm.maybe_pickoff(lead=2) is False


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
