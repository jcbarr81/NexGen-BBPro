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


def test_catch_chance_adjustments(cfg):
    # Diving 3B with 0.5s hang time and 20ft distance
    prob = catch_chance(cfg, "3B", fa=50, air_time=0.5, distance=20, diving=True)
    assert prob == pytest.approx(0.4214286, rel=1e-6)


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


def test_chase_decisions(cfg):
    assert should_chase_ball(cfg, "SS", 40) is True
    assert should_chase_ball(cfg, "P", 100) is False
    assert should_chase_ball(cfg, "CF", 120) is False
    assert should_chase_ball(cfg, "LF", 200) is True
