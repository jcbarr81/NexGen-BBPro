import random
import pytest

from logic.simulation import (
    BatterState,
    GameSimulation,
    PitcherState,
    TeamState,
)
from logic.playbalance_config import PlayBalanceConfig
from tests.test_physics import make_player, make_pitcher


def test_ground_fly_distribution():
    cfg = PlayBalanceConfig.from_dict({})
    rng = random.Random(0)
    batter = make_player("b")
    pitcher = make_pitcher("p")
    defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[pitcher])
    offense = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("op")])
    sim = GameSimulation(defense, offense, cfg, rng)
    b_state = BatterState(batter)
    p_state = PitcherState(pitcher)

    total = 5000
    ground = fly = 0
    for _ in range(total):
        sim._swing_result(
            batter, pitcher, defense, b_state, p_state, pitch_speed=90, rand=rng.random()
        )
        if sim.last_batted_ball_type == "ground":
            ground += 1
        else:
            fly += 1
    gb_rate = cfg.ground_ball_base_rate
    fb_rate = cfg.fly_ball_base_rate
    expected_ground = gb_rate / (gb_rate + fb_rate)
    expected_fly = fb_rate / (gb_rate + fb_rate)
    assert ground / total == pytest.approx(expected_ground, abs=0.02)
    assert fly / total == pytest.approx(expected_fly, abs=0.02)


def test_vert_angle_gf_pct_shifts_distribution():
    cfg0 = PlayBalanceConfig.from_dict({"vertAngleGFPct": 0})
    cfg10 = PlayBalanceConfig.from_dict({"vertAngleGFPct": 10})

    def run(cfg):
        rng = random.Random(0)
        batter = make_player("b")
        batter.gf = 0
        pitcher = make_pitcher("p")
        defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[pitcher])
        offense = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("op")])
        sim = GameSimulation(defense, offense, cfg, rng)
        b_state = BatterState(batter)
        p_state = PitcherState(pitcher)
        ground = fly = 0
        for _ in range(1000):
            sim._swing_result(
                batter, pitcher, defense, b_state, p_state, pitch_speed=90, rand=rng.random()
            )
            if sim.last_batted_ball_type == "ground":
                ground += 1
            else:
                fly += 1
        return ground, fly

    ground0, fly0 = run(cfg0)
    ground10, fly10 = run(cfg10)
    assert ground10 < ground0
    assert fly10 > fly0
