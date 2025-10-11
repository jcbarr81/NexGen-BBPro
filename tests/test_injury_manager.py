from models.player import Player
from models.roster import Roster
from services.injury_manager import place_on_injury_list, recover_from_injury


def _make_player(pid: str) -> Player:
    return Player(
        player_id=pid,
        first_name="A",
        last_name="B",
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=0,
    )


def test_injury_and_recovery_flow():
    p1 = _make_player("p1")
    p2 = _make_player("p2")
    roster = Roster(team_id="T", act=["p1"], aaa=["p2"], low=[])

    place_on_injury_list(p1, roster)

    assert p1.injured is True
    assert "p1" in roster.dl
    assert "p2" in roster.act  # replacement promoted

    recover_from_injury(p1, roster)

    assert p1.injured is False
    assert "p1" in roster.act
    assert "p2" in roster.aaa  # replacement returned to AAA
