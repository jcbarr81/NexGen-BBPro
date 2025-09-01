import random
from types import SimpleNamespace

import pytest

from logic.simulation import GameSimulation
from logic.playbalance_config import PlayBalanceConfig
from utils.path_utils import get_base_dir
from tests.test_physics import make_player, make_pitcher

PB_CFG = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")


def test_bip_distribution():
    """Ensure balls in play and fouls follow configured pitch rates."""
    rng = random.Random(0)
    batter = make_player("B", ch=50)
    pitcher = make_pitcher("P")
    sim_stub = SimpleNamespace(config=PB_CFG)

    foul_pitch_pct = PB_CFG.foulPitchBasePct / 100.0
    bip_pitch_pct = PB_CFG.ballInPlayPitchPct / 100.0
    contact_rate = foul_pitch_pct + bip_pitch_pct
    prob = GameSimulation._foul_probability(sim_stub, batter, pitcher)
    expected_foul_pct = contact_rate * prob
    expected_bip_pct = contact_rate - expected_foul_pct

    total_pitches = 100_000
    fouls = 0
    balls_in_play = 0

    for _ in range(total_pitches):
        if rng.random() < contact_rate:
            prob = GameSimulation._foul_probability(sim_stub, batter, pitcher)
            if rng.random() < prob:
                fouls += 1
            else:
                balls_in_play += 1

    bip_pct = balls_in_play / total_pitches
    foul_pct = fouls / total_pitches

    assert bip_pct == pytest.approx(expected_bip_pct, abs=0.02)
    assert foul_pct == pytest.approx(expected_foul_pct, abs=0.02)
