import random
import pytest

from logic.simulation import BatterState, GameSimulation, PitcherState, TeamState
from logic.playbalance_config import PlayBalanceConfig
from tests.test_physics import make_player, make_pitcher


def test_line_drive_distribution():
    cfg = PlayBalanceConfig.from_dict({})
    rng = random.Random(1)
    batter = make_player("b")
    pitcher = make_pitcher("p")
    defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[pitcher])
    offense = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("op")])
    sim = GameSimulation(defense, offense, cfg, rng)
    b_state = BatterState(batter)
    p_state = PitcherState(pitcher)

    total = 5000
    line = 0
    for _ in range(total):
        sim._swing_result(
            batter, pitcher, defense, b_state, p_state, pitch_speed=90, rand=rng.random()
        )
        if sim.last_batted_ball_type == "line":
            line += 1
    assert line / total == pytest.approx(0.21, abs=0.02)
