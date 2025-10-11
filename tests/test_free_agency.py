from models.player import Player
from models.team import Team
from services.free_agency import (
    list_unsigned_players,
    sign_player_to_team,
)


def make_player(pid: str) -> Player:
    return Player(
        player_id=pid,
        first_name="Test",
        last_name="Player",
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=0,
    )


def make_team() -> Team:
    return Team(
        team_id="t1",
        name="Team",
        city="City",
        abbreviation="T1",
        division="Division",
        stadium="Stadium",
        primary_color="#FFFFFF",
        secondary_color="#000000",
        owner_id="owner",
    )


def test_list_and_sign_players() -> None:
    players = {"p1": make_player("p1"), "p2": make_player("p2")}
    team = make_team()

    unsigned = list_unsigned_players(players, [team])
    assert {p.player_id for p in unsigned} == {"p1", "p2"}

    sign_player_to_team("p1", team)
    assert team.act_roster == ["p1"]

    unsigned = list_unsigned_players(players, [team])
    assert [p.player_id for p in unsigned] == ["p2"]
