from types import SimpleNamespace

from playbalance import (
    exit_velocity,
    pitch_movement,
    pitcher_fatigue,
    swing_angle,
    bat_speed,
    power_zone_factor,
    vertical_hit_angle,
    ball_roll_distance,
    air_resistance,
    control_miss_effect,
    warm_up_progress,
    pitch_velocity,
    ai_timing_adjust,
)


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


def test_swing_angle_applies_modifiers_and_randomness():
    cfg = SimpleNamespace(
        swingAngleBase=5.0,
        swingAngleGFPct=1.0,
        swingAnglePowerAdj=5.0,
        swingAngleInsideAdj=2.0,
        swingAngleRange=0.0,
    )
    angle = swing_angle(
        cfg,
        60,
        swing_type="power",
        pitch_loc="inside",
        rand=0.5,
    )
    assert angle == 12.6


def test_bat_speed_scales_with_type_and_pitch_speed():
    cfg = SimpleNamespace(
        batSpeedBase=60.0,
        batSpeedPHPct=0.5,
        batSpeedPitchSpdPct=0.2,
        batSpeedPowerPct=110.0,
        batSpeedContactPct=90.0,
        batSpeedNormalPct=100.0,
        batSpeedRefPitch=90.0,
    )
    power = bat_speed(cfg, 60, 95, swing_type="power")
    contact = bat_speed(cfg, 60, 95, swing_type="contact")
    assert power > contact


def test_vertical_hit_angle_uses_range_and_type():
    cfg = SimpleNamespace(
        hitAngleBase=10.0,
        hitAngleRange=10.0,
        hitAnglePowerAdj=5.0,
    )
    low = vertical_hit_angle(cfg, swing_type="power", rand=0.0)
    high = vertical_hit_angle(cfg, swing_type="power", rand=1.0)
    assert low == 10.0
    assert high == 20.0


def test_ball_roll_distance_accounts_for_environment():
    cfg = SimpleNamespace(
        rollSpeedMult=1.0,
        rollFrictionGrass=10.0,
        rollAltitudePct=1.0,
        rollWindPct=2.0,
    )
    base = ball_roll_distance(cfg, 100.0)
    env = ball_roll_distance(cfg, 100.0, altitude=1.0, wind_speed=5.0)
    assert env > base


def test_control_miss_effect_expands_box_and_reduces_speed():
    cfg = SimpleNamespace(
        controlBoxIncreaseEffCOPct=50.0,
        speedReductionBase=5.0,
        speedReductionEffMOPct=10.0,
    )
    box, speed = control_miss_effect(cfg, 20.0, (2.0, 3.0), 90.0)
    assert box == (12.0, 13.0)
    assert speed == 83.0


def test_warm_up_progress_caps_at_one():
    cfg = SimpleNamespace(warmUpPitches=20)
    assert warm_up_progress(cfg, 10) == 0.5
    assert warm_up_progress(cfg, 25) == 1.0


def test_power_zone_sweet_spot_gives_more_transfer():
    cfg = SimpleNamespace(
        batPowerHandleBase=25,
        batPowerHandleRange=10,
        batPowerSweetBase=90,
        batPowerSweetRange=5,
    )
    handle = power_zone_factor(cfg, "handle", rand=0.5)
    sweet = power_zone_factor(cfg, "sweet", rand=0.5)
    assert sweet > handle


def test_air_resistance_reduces_with_environmental_factors():
    cfg = SimpleNamespace(
        ballAirResistancePct=100.0,
        ballAltitudePct=50.0,
        ballBaseAltitude=0.0,
        ballTempPct=10.0,
        ballWindSpeedPct=10.0,
    )
    base = air_resistance(cfg, altitude=0.0, temperature=60.0, wind_speed=0.0)
    env = air_resistance(cfg, altitude=1000.0, temperature=80.0, wind_speed=10.0)
    assert env < base


def test_pitch_velocity_uses_range_and_rating():
    cfg = SimpleNamespace(fbSpeedBase=70, fbSpeedRange=2, fbSpeedASPct=30)
    speed = pitch_velocity(cfg, "fb", 50, rand=0.5)
    assert speed == 86.0


def test_ai_timing_adjust_combines_slop_values():
    cfg = SimpleNamespace(generalSlop=9, relaySlop=12)
    assert ai_timing_adjust(cfg, "relay", 100) == 121
