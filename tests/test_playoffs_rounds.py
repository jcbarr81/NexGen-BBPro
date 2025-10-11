from __future__ import annotations

from models.team import Team
from playbalance.playoffs_config import PlayoffsConfig
from playbalance.playoffs import generate_bracket, simulate_next_round


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


def always_home_wins(home: str, away: str, **kwargs):
    # Deterministic stub: home team always wins 1-0
    return (1, 0, "<html>box</html>", {"extra_innings": False})


def test_wc_advances_and_ds_populates_with_placeholders():
    # Two-league 6-team shape to exercise WC -> DS population.
    al = [make_team("A1", "AL East"), make_team("A2", "AL East"), make_team("A3", "AL Central"), make_team("A4", "AL Central"), make_team("A5", "AL West"), make_team("A6", "AL West")]
    nl = [make_team("N1", "NL East"), make_team("N2", "NL East"), make_team("N3", "NL Central"), make_team("N4", "NL Central"), make_team("N5", "NL West"), make_team("N6", "NL West")]
    teams = al + nl
    # Rank by wins descending within each league
    wins = {"A1": 99, "A2": 97, "A3": 95, "A4": 93, "A5": 91, "A6": 89, "N1": 98, "N2": 96, "N3": 94, "N4": 92, "N5": 90, "N6": 88}
    standings = {tid: {"wins": w, "runs_for": 700 + w, "runs_against": 650} for tid, w in wins.items()}
    cfg = PlayoffsConfig(num_playoff_teams_per_league=6)
    bracket = generate_bracket(standings, teams, cfg)

    # Simulate only WC: function advances one round at a time; call twice for both leagues
    bracket = simulate_next_round(bracket, simulate_game=always_home_wins)
    bracket = simulate_next_round(bracket, simulate_game=always_home_wins)

    # After the two calls, engine progresses depth-first; AL WC then AL DS
    names = [r.name for r in bracket.rounds]
    assert "AL DS" in names
    r_ds_al = next(r for r in bracket.rounds if r.name == "AL DS")
    assert len(r_ds_al.matchups) == 2
    seeds = [m.high.seed for m in r_ds_al.matchups]
    assert sorted(seeds) == [1, 2]

def test_generate_bracket_creates_plans_for_wildcard_structure():
    al = [make_team(f"A{i}", "AL Test") for i in range(1, 7)]
    nl = [make_team(f"N{i}", "NL Test") for i in range(1, 7)]
    teams = al + nl
    standings = {
        team.team_id: {"wins": 100 - idx, "runs_for": 700 + idx, "runs_against": 650}
        for idx, team in enumerate(teams)
    }
    cfg = PlayoffsConfig(num_playoff_teams_per_league=6)
    cfg.playoff_slots_by_league_size = {6: 6}
    bracket = generate_bracket(standings, teams, cfg)

    al_wc = next(r for r in bracket.rounds if r.name == "AL WC")
    assert len(al_wc.matchups) == 2
    al_ds = next(r for r in bracket.rounds if r.name == "AL DS")
    assert not al_ds.matchups
    assert len(al_ds.plan) == 2
    # First DS plan entry should seed #1 against a WC winner
    ref_kinds = [entry.sources[0].kind for entry in al_ds.plan]
    assert ref_kinds.count("seed") == 2
    al_cs = next(r for r in bracket.rounds if r.name == "AL CS")
    assert not al_cs.matchups
    assert len(al_cs.plan) == 1


def test_slots_for_league_defaults_and_overrides():
    cfg = PlayoffsConfig()
    assert cfg.slots_for_league(6) == 4
    assert cfg.slots_for_league(8) == 6
    assert cfg.slots_for_league(12) == 6
    assert cfg.slots_for_league(2) == 2

    cfg.playoff_slots_by_league_size = {6: 6, 8: 8}
    cfg.num_playoff_teams_per_league = 8
    assert cfg.slots_for_league(6) == 6
    # Falls back to highest <= num teams
    assert cfg.slots_for_league(9) == 8
