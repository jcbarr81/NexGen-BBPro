import csv
import random
from pathlib import Path

import logic.simulation as sim
from logic.simulation import GameSimulation, generate_boxscore
from logic.playbalance_config import PlayBalanceConfig
from scripts.simulate_season_avg import clone_team_state
from utils.lineup_loader import build_default_game_state
from utils.path_utils import get_base_dir
from utils.team_loader import load_teams


def _simulate(monkeypatch, foul_lambda=None, games: int = 20):
    teams = [t.team_id for t in load_teams()][:2]
    base_states = {tid: build_default_game_state(tid) for tid in teams}

    cfg = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")
    cfg.ballInPlayOuts = 0

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
    no_foul_p, no_foul_k = _simulate(monkeypatch, foul_lambda=lambda self, b, p: 0.0)
    foul_p, foul_k = _simulate(monkeypatch)

    csv_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "MLB_avg"
        / "mlb_avg_boxscore_2020_2024_both_teams.csv"
    )
    with csv_path.open(newline="") as f:
        row = next(csv.DictReader(f))
    mlb_pitch = float(row["TotalPitchesThrown"])
    mlb_ks = float(row["Strikeouts"])

    assert foul_p > no_foul_p
    assert abs(foul_p - mlb_pitch) < abs(no_foul_p - mlb_pitch)

    assert foul_k < no_foul_k
    assert abs(foul_k - mlb_ks) < abs(no_foul_k - mlb_ks)

