import random
import pytest

from playbalance.simulation import (
    BatterState,
    GameSimulation,
    TeamState,
)
from playbalance.state import PitcherState
from playbalance.playbalance_config import PlayBalanceConfig
from tests.test_physics import make_player, make_pitcher


def test_ground_air_distribution():
    cfg = PlayBalanceConfig.from_dict({})
    rng = random.Random(0)
    batter = make_player("b")
    pitcher = make_pitcher("p")
    defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[pitcher])
    offense = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("op")])
    sim = GameSimulation(defense, offense, cfg, rng)
    b_state = BatterState(batter)
    p_state = PitcherState()
    p_state.player = pitcher

    total = 5000
    ground = line = fly = 0
    for _ in range(total):
        sim._swing_result(
            batter, pitcher, defense, b_state, p_state, pitch_speed=90
        )
        if sim.last_batted_ball_type == "ground":
            ground += 1
        elif sim.last_batted_ball_type == "line":
            line += 1
        else:
            fly += 1
    gb_rate = cfg.ground_ball_base_rate
    ld_rate = cfg.line_drive_base_rate
    fb_rate = cfg.fly_ball_base_rate
    total_rate = gb_rate + ld_rate + fb_rate
    expected_ground = gb_rate / total_rate
    expected_air = (ld_rate + fb_rate) / total_rate
    air = line + fly
    assert ground / total == pytest.approx(expected_ground, abs=0.02)
    assert air / total == pytest.approx(expected_air, abs=0.02)


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
        p_state = PitcherState()
        p_state.player = pitcher
        ground = air = 0
        for _ in range(1000):
            sim._swing_result(
                batter, pitcher, defense, b_state, p_state, pitch_speed=90
            )
            if sim.last_batted_ball_type == "ground":
                ground += 1
            else:
                air += 1
        return ground, air

    ground0, air0 = run(cfg0)
    ground10, air10 = run(cfg10)
    assert ground10 < ground0
    assert air10 > air0
