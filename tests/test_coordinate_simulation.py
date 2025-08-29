import math
import random

import pytest

from logic.physics import Physics
from logic.fielding_ai import FieldingAI
from logic.playbalance_config import PlayBalanceConfig


def make_config() -> PlayBalanceConfig:
    cfg = PlayBalanceConfig()
    cfg.catchBaseChance = 90
    cfg.catchFADiv = 10
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
    cfg.generalSlop = 0
    cfg.shouldBeCaughtSlop = 0
    cfg.couldBeCaughtSlop = 0
    return cfg


def test_routine_fly_caught():
    cfg = make_config()
    physics = Physics(cfg, random.Random(0))
    ai = FieldingAI(cfg, random.Random(0))
    swing = physics.swing_angle(50)
    vert = physics.vertical_hit_angle()
    vx, vy, vz = physics.launch_vector(50, 50, swing, vert)
    x, y, hang = physics.landing_point(vx, vy, vz)
    fielder = (150.0, 0.0)
    distance = math.hypot(fielder[0] - x, fielder[1] - y)
    speed = physics.player_speed(50)
    run_time = distance / speed
    action = ai.catch_action(hang, run_time, position="CF", distance=distance)
    assert action == "catch"
    prob = ai.catch_probability("CF", 80, hang, action)
    assert prob == pytest.approx(1.0)
    assert ai.resolve_fly_ball("CF", 80, hang, action)


def test_diving_attempt_fails():
    cfg = make_config()
    cfg.couldBeCaughtSlop = -18
    physics = Physics(cfg, random.Random(0))
    ai = FieldingAI(cfg, random.Random(0))
    swing = physics.swing_angle(30)
    vert = physics.vertical_hit_angle()
    vx, vy, vz = physics.launch_vector(80, 80, swing, vert)
    x, y, hang = physics.landing_point(vx, vy, vz)
    fielder = (85.0, 40.0)
    distance = math.hypot(fielder[0] - x, fielder[1] - y)
    speed = physics.player_speed(50)
    run_time = distance / speed
    action = ai.catch_action(hang, run_time, position="LF", distance=distance)
    assert action == "dive"
    prob = ai.catch_probability("LF", 50, hang, action)
    assert prob == pytest.approx(0.60, abs=0.01)
    assert ai.resolve_fly_ball("LF", 50, hang, action) is False


def test_distant_ball_no_attempt():
    cfg = make_config()
    physics = Physics(cfg, random.Random(0))
    ai = FieldingAI(cfg)
    swing = physics.swing_angle(30)
    vert = physics.vertical_hit_angle()
    vx, vy, vz = physics.launch_vector(80, 80, swing, vert)
    x, y, hang = physics.landing_point(vx, vy, vz)
    fielder = (150.0, 0.0)
    distance = math.hypot(fielder[0] - x, fielder[1] - y)
    speed = physics.player_speed(50)
    run_time = distance / speed
    action = ai.catch_action(hang, run_time, position="LF", distance=distance)
    assert action == "no_attempt"
