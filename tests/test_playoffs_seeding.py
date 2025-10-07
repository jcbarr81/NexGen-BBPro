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


def test_generate_bracket_single_league_division_driven_slots():
    # Single league (AL) with 3 divisions -> 3 winners + 1 wildcard (4 total)
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

    # Expect rounds: AL DS, AL CS, Final (no wildcard round under division-based slots)
    names = [r.name for r in bracket.rounds]
    assert any(n == "AL DS" for n in names)
    assert any(n == "AL CS" for n in names)
    assert names[-1] == "Final"

    assert "AL WC" not in names

    ds = next(r for r in bracket.rounds if r.name == "AL DS")
    assert len(ds.matchups) == 2
    ds_pairs = sorted((m.high.seed, m.low.seed) for m in ds.matchups)
    assert ds_pairs == [(1, 4), (2, 3)]

    seeds = bracket.seeds_by_league["AL"]
    assert len(seeds) == 4
    assert [team.seed for team in seeds] == [1, 2, 3, 4]
    assert seeds[-1].team_id == "A2"


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


def test_generate_bracket_two_divisions_single_wildcard():
    teams = [
        make_team("A1", "AL North"),
        make_team("A2", "AL North"),
        make_team("A3", "AL South"),
        make_team("A4", "AL South"),
    ]
    standings = {
        "A1": {"wins": 95, "runs_for": 800, "runs_against": 650},
        "A2": {"wins": 90, "runs_for": 780, "runs_against": 700},
        "A3": {"wins": 94, "runs_for": 770, "runs_against": 690},
        "A4": {"wins": 85, "runs_for": 720, "runs_against": 710},
    }
    bracket = generate_bracket(standings, teams, PlayoffsConfig())

    names = [r.name for r in bracket.rounds]
    assert "AL WC" in names
    assert any(n == "AL CS" for n in names)
    assert names[-1] == "Final"

    seeds = bracket.seeds_by_league["AL"]
    assert len(seeds) == 3
    assert [team.team_id for team in seeds] == ["A1", "A3", "A2"]

    wc = next(r for r in bracket.rounds if r.name == "AL WC")
    pairs = {(m.high.team_id, m.low.team_id) for m in wc.matchups}
    assert pairs == {("A3", "A2")}

    cs = next(r for r in bracket.rounds if r.name == "AL CS")
    plan = cs.plan[0].sources
    assert plan[0].kind == "seed" and plan[0].seed == 1
    assert plan[1].kind == "winner" and plan[1].source_round == "AL WC"


def test_generate_bracket_single_league_single_word_divisions():
    teams = [
        make_team("C1", "Central"),
        make_team("C2", "Central"),
        make_team("N1", "North"),
        make_team("N2", "North"),
        make_team("S1", "South"),
        make_team("S2", "South"),
    ]
    standings = {
        "C1": {"wins": 97, "runs_for": 790, "runs_against": 660},
        "C2": {"wins": 93, "runs_for": 770, "runs_against": 680},
        "N1": {"wins": 95, "runs_for": 780, "runs_against": 670},
        "N2": {"wins": 88, "runs_for": 730, "runs_against": 700},
        "S1": {"wins": 92, "runs_for": 760, "runs_against": 690},
        "S2": {"wins": 85, "runs_for": 720, "runs_against": 710},
    }
    bracket = generate_bracket(standings, teams, PlayoffsConfig())

    assert list(bracket.seeds_by_league.keys()) == ["LEAGUE"]
    seeds = bracket.seeds_by_league["LEAGUE"]
    assert len(seeds) == 4
    assert {t.team_id for t in seeds} == {"C1", "N1", "S1", "C2"}

    names = [r.name for r in bracket.rounds]
    assert "LEAGUE DS" in names
    assert "LEAGUE CS" in names
    assert names[-1] == "Final"


def test_wildcard_is_best_remaining_team_only_once():
    teams = [
        make_team("C1", "AL Central"),
        make_team("C2", "AL Central"),
        make_team("C3", "AL Central"),
        make_team("N1", "AL North"),
        make_team("N2", "AL North"),
        make_team("N3", "AL North"),
        make_team("W1", "AL West"),
        make_team("W2", "AL West"),
        make_team("W3", "AL West"),
    ]
    standings = {
        "C1": {"wins": 96, "runs_for": 790, "runs_against": 650},
        "C2": {"wins": 94, "runs_for": 780, "runs_against": 660},
        "C3": {"wins": 80, "runs_for": 720, "runs_against": 700},
        "N1": {"wins": 97, "runs_for": 795, "runs_against": 640},
        "N2": {"wins": 92, "runs_for": 765, "runs_against": 680},
        "N3": {"wins": 84, "runs_for": 730, "runs_against": 710},
        "W1": {"wins": 95, "runs_for": 788, "runs_against": 655},
        "W2": {"wins": 91, "runs_for": 770, "runs_against": 690},
        "W3": {"wins": 83, "runs_for": 735, "runs_against": 705},
    }
    bracket = generate_bracket(standings, teams, PlayoffsConfig(num_playoff_teams_per_league=6))

    seeds = bracket.seeds_by_league["AL"]
    assert len(seeds) == 4
    # All division winners should appear
    winners = {team.team_id for team in seeds[:3]}
    assert winners == {"N1", "C1", "W1"}
    assert seeds[3].team_id == "C2"
    assert all(team.team_id != "N2" for team in seeds[3:])
