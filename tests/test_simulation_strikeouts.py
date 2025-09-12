import random
import pytest

import playbalance.simulation as sim
from playbalance.playbalance_config import PlayBalanceConfig
from playbalance.simulation import GameSimulation, generate_boxscore
from scripts.simulate_season_avg import clone_team_state
from utils.lineup_loader import build_default_game_state
from utils.path_utils import get_base_dir
from utils.team_loader import load_teams


def _simulate(monkeypatch, games: int = 20) -> float:
    teams = [t.team_id for t in load_teams()]
    base_states = {}
    for tid in teams:
        try:
            base_states[tid] = build_default_game_state(tid)
            if len(base_states) == 2:
                break
        except ValueError:
            continue
    if len(base_states) < 2:
        pytest.skip("Insufficient roster data for simulation")
    ids = list(base_states.keys())

    cfg = PlayBalanceConfig.from_file(get_base_dir() / "playbalance" / "PBINI.txt")
    rng = random.Random(0)
    total_strikeouts = 0

    with monkeypatch.context() as m:
        m.setattr(sim, "save_stats", lambda players, teams: None)
        for _ in range(games):
            home = clone_team_state(base_states[ids[0]])
            away = clone_team_state(base_states[ids[1]])
            game = GameSimulation(home, away, cfg, rng)
            game.simulate_game()
            box = generate_boxscore(home, away)
            for side in ("home", "away"):
                total_strikeouts += sum(p["so"] for p in box[side]["batting"])
    return total_strikeouts / games


def test_strikeouts_within_mlb_range(monkeypatch):
    avg_k = _simulate(monkeypatch)
    assert 15 <= avg_k <= 19
