from pathlib import Path

import scripts.physics_sim_season_kpis as kpis
from utils.lineup_autofill import auto_fill_lineup_for_team
from utils.team_loader import load_teams


def test_strikeouts_within_mlb_range(monkeypatch):
    teams = [t.team_id for t in load_teams()][:2]
    for team_id in teams:
        auto_fill_lineup_for_team(
            kpis._normalize_team_id(team_id),
            players_file="data/players.csv",
            roster_dir="data/rosters",
            lineup_dir="data/lineups",
        )

    monkeypatch.setattr(kpis, "_team_ids", lambda: teams)
    monkeypatch.setattr(kpis, "_team_parks", lambda: {})

    metrics = kpis.run_sim(
        games_per_team=10,
        seed=1,
        players_path=Path("data/players.csv"),
    )["metrics"]

    assert 0.12 <= metrics["k_pct"] <= 0.32
