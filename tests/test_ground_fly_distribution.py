import random
import pytest

from logic.simulation import GameSimulation, TeamState
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

    total = 5000
    ground = fly = 0
    for _ in range(total):
        sim._swing_result(batter, pitcher, defense, pitch_speed=90, rand=rng.random())
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
