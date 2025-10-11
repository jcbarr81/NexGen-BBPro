from models.roster import Roster
from services.roster_moves import move_player_between_rosters
import pytest


def test_move_player_between_rosters():
    roster = Roster(team_id="T", act=["p1"], aaa=["p2"], low=["p3"])

    move_player_between_rosters("p2", roster, "aaa", "act")
    assert "p2" in roster.act
    assert "p2" not in roster.aaa

    with pytest.raises(ValueError):
        move_player_between_rosters("p4", roster, "aaa", "act")

    with pytest.raises(ValueError):
        move_player_between_rosters("p1", roster, "act", "foo")
