from __future__ import annotations

from pathlib import Path
from models.team import Team
from playbalance.playoffs_config import PlayoffsConfig
from playbalance.playoffs import (
    generate_bracket,
    save_bracket,
    load_bracket,
    simulate_next_round,
)


def make_team(team_id: str, division: str) -> Team:
    return Team(
        team_id=team_id,
        name=team_id,
        city=team_id,
        abbreviation=team_id,
        division=division,
        stadium="Test Park",
        primary_color="#112233",
        secondary_color="#445566",
        owner_id="owner",
    )


def home_wins(home: str, away: str, **kwargs):
    return (1, 0, "<html>box</html>")


def test_bracket_save_and_load_round_trip(tmp_path: Path):
    # Single-league 4 teams for quick DS -> CS -> Final
    teams = [make_team("A1", "AL East"), make_team("A2", "AL East"), make_team("A3", "AL Central"), make_team("A4", "AL West")]
    standings = {tid: {"wins": w, "runs_for": 700 + w, "runs_against": 650} for tid, w in zip(["A1","A2","A3","A4"],[98,96,94,92])}
    cfg = PlayoffsConfig(num_playoff_teams_per_league=4)
    bracket = generate_bracket(standings, teams, cfg)

    # Persist to a temp file
    path = tmp_path / "playoffs.json"
    save_bracket(bracket, path)
    loaded = load_bracket(path)
    assert loaded is not None
    assert [r.name for r in loaded.rounds][0] == "AL DS"

    # Simulate next round and re-save
    loaded = simulate_next_round(loaded, simulate_game=home_wins)
    save_bracket(loaded, path)
    reloaded = load_bracket(path)
    assert reloaded is not None
    # After DS, CS should exist (may or may not be populated yet)
    assert any(r.name == "AL CS" for r in reloaded.rounds)

