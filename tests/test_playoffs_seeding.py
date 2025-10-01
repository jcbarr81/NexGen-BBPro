from __future__ import annotations

from models.team import Team
from playbalance.playoffs_config import PlayoffsConfig
from playbalance.playoffs import generate_bracket


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


def test_generate_bracket_single_league_six_team_shape():
    # Single league (AL) with 6 playoff teams -> WC + DS + CS + Final
    teams = [
        make_team("A1", "AL East"),
        make_team("A2", "AL East"),
        make_team("A3", "AL Central"),
        make_team("A4", "AL Central"),
        make_team("A5", "AL West"),
        make_team("A6", "AL West"),
    ]
    # Division winners: A1 (95), A3 (92), A5 (88); wildcards: A2 (90), A4 (89), A6 (84)
    standings = {
        "A1": {"wins": 95, "runs_for": 800, "runs_against": 650},
        "A2": {"wins": 90, "runs_for": 780, "runs_against": 700},
        "A3": {"wins": 92, "runs_for": 770, "runs_against": 690},
        "A4": {"wins": 89, "runs_for": 760, "runs_against": 710},
        "A5": {"wins": 88, "runs_for": 740, "runs_against": 710},
        "A6": {"wins": 84, "runs_for": 720, "runs_against": 715},
    }
    cfg = PlayoffsConfig(num_playoff_teams_per_league=6)
    bracket = generate_bracket(standings, teams, cfg)

    # Expect rounds: AL WC, AL DS, AL CS, Final
    names = [r.name for r in bracket.rounds]
    assert any(n == "AL WC" for n in names)
    assert any(n == "AL DS" for n in names)
    assert any(n == "AL CS" for n in names)
    assert names[-1] == "Final"

    # WC round should have 2 matchups: (3 vs 6) and (4 vs 5)
    wc = next(r for r in bracket.rounds if r.name == "AL WC")
    assert len(wc.matchups) == 2
    high_low = [(m.high.seed, m.low.seed) for m in wc.matchups]
    assert sorted(high_low) == [(3, 6), (4, 5)]


def test_generate_bracket_two_leagues_four_team_shape():
    # Two leagues (AL, NL) with 4-team brackets (straight to DS)
    al = [make_team("A1", "AL East"), make_team("A2", "AL East"), make_team("A3", "AL Central"), make_team("A4", "AL West")]
    nl = [make_team("N1", "NL East"), make_team("N2", "NL East"), make_team("N3", "NL Central"), make_team("N4", "NL West")]
    teams = al + nl
    standings = {tid: {"wins": w, "runs_for": 700 + w, "runs_against": 650} for tid, w in zip(["A1","A2","A3","A4","N1","N2","N3","N4"],[98,96,94,92,97,95,93,91])}
    cfg = PlayoffsConfig(num_playoff_teams_per_league=4)
    bracket = generate_bracket(standings, teams, cfg)

    names = [r.name for r in bracket.rounds]
    assert any(n == "AL DS" for n in names)
    assert any(n == "NL DS" for n in names)
    assert names[-1] == "WS"
    # DS pairing should be (1 vs 4) and (2 vs 3) per league
    for lg in ("AL", "NL"):
        r = next(rr for rr in bracket.rounds if rr.name == f"{lg} DS")
        pairs = [(m.high.seed, m.low.seed) for m in r.matchups]
        assert sorted(pairs) == [(1, 4), (2, 3)]

