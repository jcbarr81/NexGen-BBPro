from datetime import date
import random

from logic.player_generator import generate_player, assign_primary_position
import logic.player_generator as pg


def test_generate_player_respects_age_range():
    age_range = (30, 35)
    player = generate_player(is_pitcher=False, age_range=age_range)
    age = (date.today() - player["birthdate"]).days // 365
    assert age_range[0] <= age <= age_range[1]


def test_primary_position_override():
    # Establish what random selection would yield with this seed
    random.seed(0)
    random_choice = assign_primary_position()
    assert random_choice != "SS"
    # Reset seed so generate_player would have chosen the same random position
    random.seed(0)
    player = generate_player(is_pitcher=False, primary_position="SS")
    assert player["primary_position"] == "SS"


def test_pitcher_role_sp_when_endurance_high(monkeypatch):
    def fake_bounded_rating_high(min_val=10, max_val=99):
        fake_bounded_rating_high.calls += 1
        return 60 if fake_bounded_rating_high.calls == 1 else 50

    fake_bounded_rating_high.calls = 0
    monkeypatch.setattr(pg, "bounded_rating", fake_bounded_rating_high)

    player = generate_player(is_pitcher=True)
    assert player["endurance"] == 60
    assert player["role"] == "SP"


def test_pitcher_role_rp_when_endurance_low(monkeypatch):
    def fake_bounded_rating_low(min_val=10, max_val=99):
        fake_bounded_rating_low.calls += 1
        return 55 if fake_bounded_rating_low.calls == 1 else 50

    fake_bounded_rating_low.calls = 0
    monkeypatch.setattr(pg, "bounded_rating", fake_bounded_rating_low)

    player = generate_player(is_pitcher=True)
    assert player["endurance"] == 55
    assert player["role"] == "RP"
