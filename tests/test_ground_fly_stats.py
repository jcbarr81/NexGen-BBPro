import random

import pytest

from logic.simulation import (
    BatterState,
    GameSimulation,
    PitcherState,
    TeamState,
)
from logic.playbalance_config import PlayBalanceConfig
from logic.stats import compute_batting_rates, compute_pitching_rates
from tests.test_physics import make_player, make_pitcher


def test_swing_result_tracks_ground_fly(monkeypatch):
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
    p_state = PitcherState(pitcher)
    sim._swing_result(batter, pitcher, defense, b_state, p_state, pitch_speed=90, rand=0.0)
    assert b_state.gb == 1 and p_state.gb == 1 and b_state.fb == 0 and p_state.fb == 0

    cfg_fb = PlayBalanceConfig.from_dict({"groundBallBaseRate": 0, "flyBallBaseRate": 100})
    sim_fly = GameSimulation(defense, offense, cfg_fb, random.Random(0))
    monkeypatch.setattr(sim_fly.fielding_ai, "catch_action", lambda *a, **k: "no_attempt")
    monkeypatch.setattr(sim_fly.physics, "landing_point", lambda *a, **k: (100.0, 0.0, 1.0))
    monkeypatch.setattr(sim_fly.physics, "ball_roll_distance", lambda *a, **k: 0.0)
    monkeypatch.setattr(sim_fly.physics, "ball_bounce", lambda *a, **k: (0.0, 0.0))
    b_state2 = BatterState(batter)
    p_state2 = PitcherState(pitcher)
    sim_fly._swing_result(
        batter, pitcher, defense, b_state2, p_state2, pitch_speed=90, rand=0.0
    )
    assert b_state2.fb == 1 and p_state2.fb == 1 and b_state2.gb == 0 and p_state2.gb == 0


def test_ground_fly_rates():
    batter = make_player("b")
    bs = BatterState(batter)
    bs.gb = 30
    bs.fb = 20
    rates = compute_batting_rates(bs)
    assert rates["gb_pct"] == pytest.approx(0.6)
    assert rates["fb_pct"] == pytest.approx(0.4)
    assert rates["gb_fb"] == pytest.approx(1.5)

    pitcher = make_pitcher("p")
    ps = PitcherState(pitcher)
    ps.gb = 40
    ps.fb = 10
    prates = compute_pitching_rates(ps)
    assert prates["gb_pct"] == pytest.approx(0.8)
    assert prates["fb_pct"] == pytest.approx(0.2)
    assert prates["gb_fb"] == pytest.approx(4.0)
