from playbalance.training_camp import run_training_camp
from models.player import Player


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


def test_training_camp_sets_ready_flag() -> None:
    players = [make_player("p1"), make_player("p2")]
    assert all(not p.ready for p in players)

    run_training_camp(players)
    assert all(p.ready for p in players)
