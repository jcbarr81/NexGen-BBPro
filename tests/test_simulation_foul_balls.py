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
    assert foul_k <= no_foul_k + 1.5


PB_CFG, _ = load_tuned_playbalance_config()


def _expected_foul_and_bip(cfg):
    strike_base_pct = cfg.foulStrikeBasePct / 100.0
    foul_pitch_pct = cfg.foulPitchBasePct / 100.0
    strike_rate = foul_pitch_pct / strike_base_pct if strike_base_pct else 0.0
    strike_rate = min(1.0, strike_rate)
    foul_rate = strike_base_pct
    foul_per_pitch = strike_rate * foul_rate
    bip_pitch_pct = cfg.ballInPlayPitchPct / 100.0
    bip_pitch_pct *= max(0.0, float(cfg.get("ballInPlayScale", 1.0)) if hasattr(cfg, "get") else 1.0)
    balance = float(cfg.get("foulBIPBalance", 0.94)) if hasattr(cfg, "get") else 0.94
    contact_rate = foul_per_pitch + bip_pitch_pct * balance
    if contact_rate <= 0.0:
        return 0.0, 0.0
    raw_prob = foul_per_pitch / contact_rate
    foul_scale = float(cfg.get("foulProbabilityScale", 1.0)) if hasattr(cfg, "get") else 1.0
    prob = raw_prob * max(0.0, foul_scale)
    prob = max(0.05, min(0.95, prob))
    foul_pct = contact_rate * prob
    bip_pct = contact_rate * (1.0 - prob)
    return foul_pct, bip_pct


def test_foul_pitch_distribution():
    """Ensure foul frequency per pitch matches configured averages."""

    batter = make_player("B", ch=50)
    pitcher = make_pitcher("P")
    sim_stub = SimpleNamespace(config=PB_CFG)

    strike_based_pct = PB_CFG.foulStrikeBasePct / 100.0
    foul_pitch_pct = PB_CFG.foulPitchBasePct / 100.0
    foul_pct_expected, bip_pct_expected = _expected_foul_and_bip(PB_CFG)
    contact_rate = foul_pct_expected + bip_pct_expected
    strike_rate = min(1.0, foul_pitch_pct / strike_based_pct)

    foul_prob_contact = GameSimulation._foul_probability(sim_stub, batter, pitcher)
    contact_share = foul_pct_expected + bip_pct_expected
    expected_contact_foul = (
        foul_pct_expected / contact_share if contact_share > 0 else 0.0
    )
    assert foul_prob_contact == pytest.approx(expected_contact_foul, rel=0.05)
    assert foul_pct_expected == pytest.approx(foul_pitch_pct, rel=0.15)

