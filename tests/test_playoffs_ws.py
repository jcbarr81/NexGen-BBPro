from __future__ import annotations

from models.team import Team
from playbalance.playoffs_config import PlayoffsConfig
from playbalance.playoffs import generate_bracket, simulate_next_round, simulate_playoffs


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


def test_ws_population_and_champion_resolution():
    # Two-league, 4 teams per league for minimal bracket length
    al = [make_team("A1", "AL East"), make_team("A2", "AL East"), make_team("A3", "AL Central"), make_team("A4", "AL West")]
    nl = [make_team("N1", "NL East"), make_team("N2", "NL East"), make_team("N3", "NL Central"), make_team("N4", "NL West")]
    teams = al + nl
    standings = {tid: {"wins": w, "runs_for": 700 + w, "runs_against": 650} for tid, w in zip(["A1","A2","A3","A4","N1","N2","N3","N4"],[98,96,94,92,97,95,93,91])}
    cfg = PlayoffsConfig(num_playoff_teams_per_league=4)
    bracket = generate_bracket(standings, teams, cfg)

    # Progress through DS and CS for both leagues then populate WS
    bracket = simulate_next_round(bracket, simulate_game=home_wins)  # AL DS
    bracket = simulate_next_round(bracket, simulate_game=home_wins)  # NL DS
    bracket = simulate_next_round(bracket, simulate_game=home_wins)  # AL CS
    bracket = simulate_next_round(bracket, simulate_game=home_wins)  # NL CS

    # Now simulate the WS to completion; ensure champion set
    bracket = simulate_playoffs(bracket, simulate_game=home_wins, persist_cb=lambda b: None)
    assert bracket.champion is not None
    assert bracket.runner_up is not None

