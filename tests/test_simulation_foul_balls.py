import csv
import random
from types import SimpleNamespace
from pathlib import Path

import pytest

import logic.simulation as sim
from logic.simulation import GameSimulation, generate_boxscore
from logic.playbalance_config import PlayBalanceConfig
from scripts.simulate_season_avg import clone_team_state
from utils.lineup_loader import build_default_game_state
from utils.path_utils import get_base_dir
from utils.team_loader import load_teams
from tests.test_physics import make_player, make_pitcher


def _simulate(monkeypatch, foul_lambda=None, min_misread_contact=None, games: int = 20):
    teams = [t.team_id for t in load_teams()][:2]
    base_states = {tid: build_default_game_state(tid) for tid in teams}

    cfg = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")
    cfg.ballInPlayOuts = 0
    if min_misread_contact is not None:
        cfg.minMisreadContact = min_misread_contact

    rng = random.Random(42)
    total_pitches = 0
    total_strikeouts = 0

    with monkeypatch.context() as m:
        m.setattr(sim, "save_stats", lambda players, teams: None)
        if foul_lambda is not None:
            m.setattr(GameSimulation, "_foul_probability", foul_lambda)

        for _ in range(games):
            home = clone_team_state(base_states[teams[0]])
            away = clone_team_state(base_states[teams[1]])
            game = GameSimulation(home, away, cfg, rng)
            game.simulate_game()
            box = generate_boxscore(home, away)
            for side in ("home", "away"):
                batting = box[side]["batting"]
                pitching = box[side]["pitching"]
                total_strikeouts += sum(p["so"] for p in batting)
                total_pitches += sum(p["pitches"] for p in pitching)

    return total_pitches / games, total_strikeouts / games


def test_fouls_increase_pitches_reduce_strikeouts(monkeypatch):
    no_foul_p, no_foul_k = _simulate(
        monkeypatch, foul_lambda=lambda self, b, p, **kw: 0.0
    )
    foul_p, foul_k = _simulate(monkeypatch)

    assert foul_p > no_foul_p
    assert foul_k < no_foul_k


PB_CFG = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")


@pytest.mark.parametrize(
    "base_pct, trend_pct",
    [(PB_CFG.foulStrikeBasePct / 100.0, PB_CFG.foulContactTrendPct / 100.0)],
)
def test_foul_strike_distribution(base_pct, trend_pct):
    """Ensure foul strikes match configured league averages."""

    rng = random.Random(0)
    batter = make_player("B", ch=50)
    pitcher = make_pitcher("P")
    sim_stub = SimpleNamespace(config=PB_CFG)

    contact_rate = min(1.0, 2 * base_pct)
    total_strikes = 100_000
    foul_strikes = 0
    balls_in_play = 0

    for _ in range(total_strikes):
        if rng.random() < contact_rate:
            prob = GameSimulation._foul_probability(sim_stub, batter, pitcher)
            if rng.random() < prob:
                foul_strikes += 1
            else:
                balls_in_play += 1

    foul_pct = foul_strikes / total_strikes
    assert foul_pct == pytest.approx(base_pct, abs=0.01)
    assert foul_strikes == pytest.approx(balls_in_play, rel=0.02)

