import random
import pytest

from logic.simulation import (
    BatterState,
    GameSimulation,
    TeamState,
)
from playbalance.state import PitcherState
from logic.playbalance_config import PlayBalanceConfig
from tests.test_physics import make_player, make_pitcher


def test_bip_type_distribution():
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
    counts = {"ground": 0, "line": 0, "fly": 0}
    for _ in range(total):
        sim._swing_result(
            batter, pitcher, defense, b_state, p_state, pitch_speed=90
        )
        counts[sim.last_batted_ball_type] += 1

    gb = cfg.ground_ball_base_rate
    ld = cfg.line_drive_base_rate
    fb = cfg.fly_ball_base_rate
    total_rate = gb + ld + fb
    assert counts["ground"] / total == pytest.approx(gb / total_rate, abs=0.02)
    assert counts["line"] / total == pytest.approx(ld / total_rate, abs=0.02)
    assert counts["fly"] / total == pytest.approx(fb / total_rate, abs=0.02)
