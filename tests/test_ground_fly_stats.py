import random

import pytest

from playbalance.simulation import (
    BatterState,
    GameSimulation,
    TeamState,
)
from playbalance.state import PitcherState
from playbalance.playbalance_config import PlayBalanceConfig
from playbalance.stats import compute_batting_rates, compute_pitching_rates
from tests.test_physics import make_player, make_pitcher


def test_swing_result_tracks_ground_line_fly(monkeypatch):
    cfg_gb = PlayBalanceConfig.from_dict({"groundBallBaseRate": 100, "flyBallBaseRate": 0})
    batter = make_player("b")
    pitcher = make_pitcher("p")
    defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[pitcher])
    offense = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("op")])
    sim = GameSimulation(defense, offense, cfg_gb, random.Random(0))
    monkeypatch.setattr(sim.fielding_ai, "catch_action", lambda *a, **k: "no_attempt")
    monkeypatch.setattr(sim.physics, "landing_point", lambda *a, **k: (100.0, 0.0, 1.0))
    monkeypatch.setattr(sim.physics, "ball_roll_distance", lambda *a, **k: 0.0)
    monkeypatch.setattr(sim.physics, "ball_bounce", lambda *a, **k: (0.0, 0.0))
    b_state = BatterState(batter)
    p_state = PitcherState()
    p_state.player = pitcher
    sim._swing_result(batter, pitcher, defense, b_state, p_state, pitch_speed=90)
    assert (
        b_state.gb == 1
        and p_state.gb == 1
        and b_state.ld == 0
        and b_state.fb == 0
    )

    cfg_fb = PlayBalanceConfig.from_dict({"groundBallBaseRate": 0, "flyBallBaseRate": 100})

    sim_line = GameSimulation(defense, offense, cfg_fb, random.Random(0))
    monkeypatch.setattr(sim_line.fielding_ai, "catch_action", lambda *a, **k: "no_attempt")
    monkeypatch.setattr(sim_line.physics, "landing_point", lambda *a, **k: (100.0, 0.0, 1.0))
    monkeypatch.setattr(sim_line.physics, "ball_roll_distance", lambda *a, **k: 0.0)
    monkeypatch.setattr(sim_line.physics, "ball_bounce", lambda *a, **k: (0.0, 0.0))
    monkeypatch.setattr(sim_line.physics, "vertical_hit_angle", lambda *a, **k: 10.0)
    b_state_line = BatterState(batter)
    p_state_line = PitcherState()
    p_state_line.player = pitcher
    sim_line._swing_result(
        batter, pitcher, defense, b_state_line, p_state_line, pitch_speed=90
    )
    assert (
        b_state_line.ld == 1
        and p_state_line.ld == 1
        and b_state_line.gb == 0
        and b_state_line.fb == 0
    )

    sim_fly = GameSimulation(defense, offense, cfg_fb, random.Random(0))
    monkeypatch.setattr(sim_fly.fielding_ai, "catch_action", lambda *a, **k: "no_attempt")
    monkeypatch.setattr(sim_fly.physics, "landing_point", lambda *a, **k: (100.0, 0.0, 1.0))
    monkeypatch.setattr(sim_fly.physics, "ball_roll_distance", lambda *a, **k: 0.0)
    monkeypatch.setattr(sim_fly.physics, "ball_bounce", lambda *a, **k: (0.0, 0.0))
    monkeypatch.setattr(sim_fly.physics, "vertical_hit_angle", lambda *a, **k: 20.0)
    b_state_fly = BatterState(batter)
    p_state_fly = PitcherState()
    p_state_fly.player = pitcher
    sim_fly._swing_result(
        batter, pitcher, defense, b_state_fly, p_state_fly, pitch_speed=90
    )
    assert (
        b_state_fly.fb == 1
        and p_state_fly.fb == 1
        and b_state_fly.gb == 0
        and b_state_fly.ld == 0
    )


def test_batted_ball_rates():
    batter = make_player("b")
    bs = BatterState(batter)
    bs.gb = 30
    bs.ld = 10
    bs.fb = 20
    rates = compute_batting_rates(bs)
    assert rates["gb_pct"] == pytest.approx(0.5)
    assert rates["ld_pct"] == pytest.approx(1 / 6)
    assert rates["fb_pct"] == pytest.approx(1 / 3)
    assert rates["gb_fb"] == pytest.approx(1.5)
    assert rates["ld_fb_ratio"] == pytest.approx(0.5)

    pitcher = make_pitcher("p")
    ps = PitcherState()
    ps.player = pitcher
    ps.gb = 40
    ps.ld = 10
    ps.fb = 10
    prates = compute_pitching_rates(ps)
    assert prates["gb_pct"] == pytest.approx(2 / 3)
    assert prates["ld_pct"] == pytest.approx(1 / 6)
    assert prates["fb_pct"] == pytest.approx(1 / 6)
    assert prates["gb_fb"] == pytest.approx(4.0)
    assert prates["ld_fb_ratio"] == pytest.approx(1.0)
