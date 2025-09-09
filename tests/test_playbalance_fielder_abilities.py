import pytest

from playbalance import (
    load_config,
    reaction_delay,
    catch_chance,
    max_throw_distance,
    throw_speed,
    good_throw_chance,
    wild_pitch_catch_chance,
    should_chase_ball,
)


@pytest.fixture(scope="module")
def cfg():
    """Return a PlayBalanceConfig loaded from the project's PBINI file."""

    return load_config()


def test_reaction_delay(cfg):
    assert reaction_delay(cfg, "C", 50) == 10.0


def test_reaction_delay_scales_with_skill(cfg):
    """Higher fielding ability should reduce reaction time."""

    mid = reaction_delay(cfg, "C", 50)
    high = reaction_delay(cfg, "C", 80)
    low = reaction_delay(cfg, "C", 0)
    assert high < mid < low
    assert high == pytest.approx(8.8)


def test_catch_chance_adjustments(cfg):
    # Diving 3B with 0.5s hang time and 20ft distance
    prob = catch_chance(cfg, "3B", fa=50, air_time=0.5, distance=20, diving=True)
    assert prob == pytest.approx(0.4214286, rel=1e-6)


def test_automatic_catch_distance(cfg):
    """Balls within the automatic catch radius are always caught."""

    assert catch_chance(cfg, "2B", fa=10, air_time=2.0, distance=10) == 1.0


def test_throwing_metrics(cfg):
    assert max_throw_distance(cfg, 50) == 240
    assert throw_speed(cfg, 150, 60) == pytest.approx(56.5)
    # Large distance capped at max speed for outfielders
    assert throw_speed(cfg, 2000, 60, outfielder=True) == cfg.throwSpeedOFMax


def test_throw_accuracy_and_wild_pitch(cfg):
    # CF accuracy
    assert good_throw_chance(cfg, "CF", 80) == pytest.approx(0.85)
    # Wild pitch catch chance with cross-body adjustment
    assert wild_pitch_catch_chance(cfg, 20, cross_body=True) == pytest.approx(0.85)


def test_good_throw_chance_clamped(cfg):
    """Throw accuracy chance should not exceed 100%."""

    assert good_throw_chance(cfg, "P", 500) == 1.0


def test_wild_pitch_high_modifier(cfg):
    """High wild pitches apply their modifier to the catch chance."""

    assert wild_pitch_catch_chance(cfg, 20, high=True) == pytest.approx(0.9)


def test_chase_decisions(cfg):
    assert should_chase_ball(cfg, "SS", 40) is True
    assert should_chase_ball(cfg, "P", 100) is False
    assert should_chase_ball(cfg, "CF", 120) is False
    assert should_chase_ball(cfg, "LF", 200) is True


def test_outfield_chase_threshold(cfg):
    """Outfielders only chase once distance meets configured threshold."""

    dist = cfg.outfieldMinChaseDist
    assert should_chase_ball(cfg, "LF", dist - 1) is False
    assert should_chase_ball(cfg, "LF", dist) is True


def test_catch_chance_pbini_range(cfg):
    """Catch probabilities respect PBINI base and maximum values."""

    low = catch_chance(cfg, "SS", fa=0, air_time=1.2, distance=20)
    assert low == pytest.approx(cfg.catchBaseChance / 100)
    high = catch_chance(cfg, "SS", fa=100, air_time=1.2, distance=20)
    expected_high = min(
        100, cfg.catchBaseChance + 100 / cfg.catchFADiv
    )
    assert high == pytest.approx(expected_high / 100)


def test_throw_distance_speed_pbini_range(cfg):
    """Throw distance and speed scale according to PBINI settings."""

    assert max_throw_distance(cfg, 0) == cfg.maxThrowDistBase
    assert max_throw_distance(cfg, 100) == (
        cfg.maxThrowDistBase + cfg.maxThrowDistASPct
    )
    assert throw_speed(cfg, 0, 0) == cfg.throwSpeedIFBase
    expected = (
        cfg.throwSpeedIFBase
        + cfg.throwSpeedIFDistPct * 100 / 100
        + cfg.throwSpeedIFASPct * 50 / 100
    )
    assert throw_speed(cfg, 100, 50) == pytest.approx(expected)


def test_good_throw_chance_pbini_range(cfg):
    """Good throw chance adheres to PBINI-configured limits."""

    low = good_throw_chance(cfg, "SS", 0)
    expected_low = (cfg.goodThrowBase + cfg.goodThrowChanceShortStop) / 100
    assert low == pytest.approx(expected_low)
    assert good_throw_chance(cfg, "SS", 100) == 1.0


def test_wild_pitch_catch_chance_pbini_range(cfg):
    """Wild pitch catch chance scales with rating per PBINI values."""

    base = wild_pitch_catch_chance(cfg, 0)
    assert base == pytest.approx(cfg.wildCatchChanceBase / 100)
    high = wild_pitch_catch_chance(cfg, 100)
    expected_high = min(
        100, cfg.wildCatchChanceBase + cfg.wildCatchChanceFAPct
    )
    assert high == pytest.approx(expected_high / 100)
