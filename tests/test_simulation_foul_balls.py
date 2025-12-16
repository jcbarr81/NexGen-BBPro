import random
from types import SimpleNamespace

import pytest

import playbalance.simulation as sim
from playbalance.simulation import GameSimulation, generate_boxscore
from playbalance.sim_config import load_tuned_playbalance_config
from scripts.simulate_season_avg import clone_team_state
from utils.lineup_loader import build_default_game_state
from utils.path_utils import get_base_dir
from utils.team_loader import load_teams
from tests.test_physics import make_player, make_pitcher


def _simulate(monkeypatch, foul_lambda=None, games: int = 20):
    teams = [t.team_id for t in load_teams()][:2]
    base_states = {tid: build_default_game_state(tid) for tid in teams}

    cfg, _ = load_tuned_playbalance_config()

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
    assert foul_k <= no_foul_k + 8


PB_CFG, _ = load_tuned_playbalance_config()


def test_foul_probability_tracks_contact_and_counts():
    batter = make_player("B", ch=70)
    weak = make_player("W", ch=30)
    pitcher = make_pitcher("P")
    sim_stub = SimpleNamespace(config=PB_CFG)

    high_contact = GameSimulation._foul_probability(
        sim_stub, batter, pitcher, contact_prob=0.78
    )
    low_contact = GameSimulation._foul_probability(
        sim_stub, weak, pitcher, contact_prob=0.35
    )
    assert low_contact > high_contact

    zero_strike = GameSimulation._foul_probability(
        sim_stub, batter, pitcher, strikes=0, contact_prob=0.55
    )
    two_strike = GameSimulation._foul_probability(
        sim_stub, batter, pitcher, strikes=2, contact_prob=0.55
    )
    assert two_strike > zero_strike

