import random

from playbalance.simulation import BatterState, GameSimulation, TeamState
from playbalance.state import PitcherState
from playbalance.playbalance_config import PlayBalanceConfig
from tests.test_physics import make_player, make_pitcher


def _simulate_counts(batter, pitcher, cfg):
    """Helper to simulate a large number of swings and return type counts."""
    defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[pitcher])
    offense = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("op")])
    sim = GameSimulation(defense, offense, cfg, random.Random(0))
    b_state = BatterState(batter)
    p_state = PitcherState()
    p_state.player = pitcher
    counts = {"ground": 0, "line": 0, "fly": 0}
    for _ in range(3000):
        sim._swing_result(batter, pitcher, defense, b_state, p_state, pitch_speed=90)
        counts[sim.last_batted_ball_type] += 1
    return counts


def test_batter_attributes_shift_distribution():
    cfg = PlayBalanceConfig.from_dict({})
    slugger = make_player("slug", ph=80)
    slugger.gf = 80
    slap = make_player("slap", ph=20)
    slap.gf = 20
    pitcher = make_pitcher("p")
    slug_counts = _simulate_counts(slugger, pitcher, cfg)
    slap_counts = _simulate_counts(slap, pitcher, cfg)
    assert slug_counts["fly"] > slap_counts["fly"]
    assert slug_counts["ground"] < slap_counts["ground"]


def test_pitcher_movement_shift_distribution():
    cfg = PlayBalanceConfig.from_dict({})
    batter = make_player("b")
    ground_pitcher = make_pitcher("g")
    ground_pitcher.movement = 80
    fly_pitcher = make_pitcher("f")
    fly_pitcher.movement = 20
    ground_counts = _simulate_counts(batter, ground_pitcher, cfg)
    fly_counts = _simulate_counts(batter, fly_pitcher, cfg)
    assert ground_counts["ground"] > fly_counts["ground"]
    assert ground_counts["fly"] < fly_counts["fly"]

