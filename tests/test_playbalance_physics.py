from types import SimpleNamespace

from playbalance import exit_velocity, pitch_movement, pitcher_fatigue


def test_exit_velocity_scales_with_swing_type():
    cfg = SimpleNamespace(
        exitVeloBase=50.0,
        exitVeloPHPct=1.0,
        exitVeloPowerPct=120.0,
        exitVeloNormalPct=100.0,
        exitVeloContactPct=80.0,
    )
    power = exit_velocity(cfg, 60, swing_type="power")
    contact = exit_velocity(cfg, 60, swing_type="contact")
    assert power > contact


def test_pitch_movement_uses_config_and_randomness():
    cfg = SimpleNamespace(
        fbBreakBaseWidth=1.0,
        fbBreakBaseHeight=2.0,
        fbBreakRangeWidth=2.0,
        fbBreakRangeHeight=4.0,
    )
    dx, dy = pitch_movement(cfg, "fb", rand=0.5)
    assert dx == 2.0 and dy == 4.0


def test_pitcher_fatigue_thresholds():
    cfg = SimpleNamespace(pitcherTiredThresh=20, pitcherExhaustedThresh=5)
    remaining, state = pitcher_fatigue(cfg, 100, 0)
    assert remaining == 100 and state == "fresh"
    remaining, state = pitcher_fatigue(cfg, 100, 82)
    assert remaining == 18 and state == "tired"
    remaining, state = pitcher_fatigue(cfg, 100, 97)
    assert remaining == 3 and state == "exhausted"
