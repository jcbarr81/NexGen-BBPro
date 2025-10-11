from playbalance.bullpen import WarmupTracker
from tests.util.pbini_factory import make_cfg

def test_warmup_becomes_ready():
    cfg = make_cfg(
        warmupPitchCount=2,
        warmupSecsPerWarmPitch=10,
    )
    tracker = WarmupTracker(cfg)
    tracker.warm_pitch()
    assert not tracker.is_ready()
    tracker.warm_pitch()
    assert tracker.is_ready()
    assert tracker.pitches == 2
    assert tracker.elapsed == 20


def test_maintenance_resets_timer():
    cfg = make_cfg(
        warmupPitchCount=1,
        warmupSecsPerWarmPitch=10,
        warmupSecsPerMaintPitch=5,
        warmupSecsBeforeCool=15,
        warmupSecsPerCoolPitch=5,
    )
    tracker = WarmupTracker(cfg)
    tracker.warm_pitch()
    tracker.advance(10)
    assert tracker.is_ready()
    tracker.maintain_pitch()
    tracker.advance(10)
    assert tracker.is_ready()


def test_cooldown_reduces_pitches():
    cfg = make_cfg(
        warmupPitchCount=2,
        warmupSecsPerWarmPitch=10,
        warmupSecsBeforeCool=0,
        warmupSecsPerCoolPitch=5,
    )
    tracker = WarmupTracker(cfg)
    tracker.warm_pitch()
    tracker.warm_pitch()
    assert tracker.is_ready()
    tracker.advance(5)
    assert tracker.pitches == 1
    tracker.advance(5)
    assert tracker.pitches == 0
    assert not tracker.is_ready()
