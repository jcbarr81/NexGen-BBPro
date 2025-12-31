from pathlib import Path

import scripts.physics_sim_season_kpis as kpis
from utils.team_loader import load_teams
from utils.lineup_autofill import auto_fill_lineup_for_team


def test_simulated_averages_close_to_mlb(monkeypatch):
    """Run a short physics-sim sample and ensure KPIs stay in reasonable bands."""

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

    assert 0.20 <= metrics["avg"] <= 0.35
    assert 0.25 <= metrics["obp"] <= 0.42
    assert 0.30 <= metrics["slg"] <= 0.60
    assert 3.3 <= metrics["pitches_per_pa"] <= 4.4
    assert 0.12 <= metrics["k_pct"] <= 0.32
    assert 0.05 <= metrics["bb_pct"] <= 0.14
