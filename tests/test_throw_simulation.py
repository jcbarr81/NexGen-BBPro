from __future__ import annotations

import math

import pytest

from logic.physics import Physics
from tests.util.pbini_factory import make_cfg


def test_throw_velocity_and_time_differ_by_position():
    cfg = make_cfg(
        maxThrowDistBase=100,
        maxThrowDistASPct=50,
        throwSpeedIFBase=10,
        throwSpeedIFDistPct=10,
        throwSpeedIFMax=15,
        throwSpeedOFBase=10,
        throwSpeedOFDistPct=10,
        throwSpeedOFMax=25,
    )
    physics = Physics(cfg)
    assert physics.max_throw_distance(50) == pytest.approx(125)

    dist = 100
    v_if = physics.throw_velocity(dist, outfield=False)
    v_of = physics.throw_velocity(dist, outfield=True)
    assert v_if == pytest.approx(15)
    assert v_of == pytest.approx(20)

    t_if = physics.throw_time(50, dist, position="SS")
    t_of = physics.throw_time(50, dist, position="LF")
    assert t_of < t_if


def test_throw_time_infinite_beyond_max_range():
    cfg = make_cfg(
        maxThrowDistBase=100,
        maxThrowDistASPct=0,
        throwSpeedIFBase=10,
        throwSpeedIFDistPct=0,
        throwSpeedIFMax=10,
        throwSpeedOFBase=10,
        throwSpeedOFDistPct=0,
        throwSpeedOFMax=10,
    )
    physics = Physics(cfg)
    assert math.isinf(physics.throw_time(0, 150, position="SS"))
