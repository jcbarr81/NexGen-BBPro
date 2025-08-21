from datetime import date
from unittest.mock import patch

from logic.aging import age_player
from models.pitcher import Pitcher


def _make_pitcher() -> Pitcher:
    today = date.today()
    birthdate = date(today.year - 25, today.month, today.day).isoformat()
    return Pitcher(
        player_id="p",
        first_name="Test",
        last_name="Pitcher",
        birthdate=birthdate,
        height=72,
        weight=180,
        bats="R",
        primary_position="SP",
        other_positions=[],
        gf=0,
        endurance=50,
        control=50,
        movement=50,
        hold_runner=50,
        role="SP",
        fb=60,
        cu=50,
        cb=40,
        sl=30,
        si=20,
        scb=10,
        kn=0,
        arm=50,
        fa=50,
    )


def test_spring_training_pitch_increases_selected_rating():
    pitcher = _make_pitcher()
    with patch("logic.aging.random.choice", return_value="sl"):
        age_player(pitcher)
    assert pitcher.sl == int(round(30 * 1.35))
    assert pitcher.fb == 60
