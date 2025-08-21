from collections import Counter
from datetime import date
import random

from logic.player_generator import (
    generate_player,
    assign_primary_position,
    generate_birthdate,
)
import logic.player_generator as pg


def test_generate_player_respects_age_range():
    age_range = (30, 35)
    player = generate_player(is_pitcher=False, age_range=age_range)
    age = (date.today() - player["birthdate"]).days // 365
    assert age_range[0] <= age <= age_range[1]


def test_generate_birthdate_respects_age_tables():
    trials = 100
    for ptype, (base, dice, sides) in pg.AGE_TABLES.items():
        ages = [generate_birthdate(player_type=ptype)[1] for _ in range(trials)]
        assert min(ages) >= base + dice
        assert max(ages) <= base + dice * sides


def test_generate_player_uses_age_table_for_draft():
    player = generate_player(is_pitcher=False, for_draft=True)
    age = (date.today() - player["birthdate"]).days // 365
    base, dice, sides = pg.AGE_TABLES["amateur"]
    assert base + dice <= age <= base + dice * sides


def test_generate_player_allows_explicit_player_type():
    player = generate_player(is_pitcher=False, player_type="filler")
    age = (date.today() - player["birthdate"]).days // 365
    base, dice, sides = pg.AGE_TABLES["filler"]
    assert base + dice <= age <= base + dice * sides


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
    def fake_distribute(total, weights):
        fake_distribute.calls += 1
        if fake_distribute.calls == 1:
            return {
                "endurance": 60,
                "control": 50,
                "movement": 50,
                "hold_runner": 50,
                "arm": 50,
            }
        return {k: 50 for k in weights}

    fake_distribute.calls = 0
    monkeypatch.setattr(pg, "distribute_rating_points", fake_distribute)

    player = generate_player(is_pitcher=True)
    assert player["endurance"] == 60
    assert player["role"] == "SP"


def test_pitcher_role_rp_when_endurance_low(monkeypatch):
    def fake_distribute(total, weights):
        fake_distribute.calls += 1
        if fake_distribute.calls == 1:
            return {
                "endurance": 55,
                "control": 50,
                "movement": 50,
                "hold_runner": 50,
                "arm": 50,
            }
        return {k: 50 for k in weights}

    fake_distribute.calls = 0
    monkeypatch.setattr(pg, "distribute_rating_points", fake_distribute)

    player = generate_player(is_pitcher=True)
    assert player["endurance"] == 55
    assert player["role"] == "RP"


def test_pitcher_can_hit(monkeypatch):
    def fake_randint(a, b):
        if (a, b) == (1, 100):
            fake_randint.calls += 1
            return 1 if fake_randint.calls == 2 else 50
        if (a, b) == (10, 99):
            return 80
        return (a + b) // 2

    fake_randint.calls = 0
    monkeypatch.setattr(pg.random, "randint", fake_randint)

    player = generate_player(is_pitcher=True)
    assert player["ch"] == int(80 * 0.75)
    assert player["pot_ch"] >= player["ch"]


def test_lefty_pitcher_adjustment(monkeypatch):
    def fake_distribute(total, weights):
        fake_distribute.calls += 1
        if fake_distribute.calls == 1:
            return {
                "endurance": 50,
                "control": 60,
                "movement": 60,
                "hold_runner": 50,
                "arm": 50,
            }
        return {k: 50 for k in weights}

    fake_distribute.calls = 0
    monkeypatch.setattr(pg, "distribute_rating_points", fake_distribute)
    monkeypatch.setattr(pg, "assign_bats_throws", lambda _: ("R", "L"))

    player = generate_player(is_pitcher=True)
    assert player["movement"] == 70
    assert player["control"] == 50


def test_lefty_pitcher_adjustment_respects_caps(monkeypatch):
    def fake_distribute(total, weights):
        fake_distribute.calls += 1
        if fake_distribute.calls == 1:
            return {
                "endurance": 50,
                "control": 55,
                "movement": 85,
                "hold_runner": 50,
                "arm": 50,
            }
        return {k: 50 for k in weights}

    fake_distribute.calls = 0
    monkeypatch.setattr(pg, "distribute_rating_points", fake_distribute)
    monkeypatch.setattr(pg, "assign_bats_throws", lambda _: ("R", "L"))

    player = generate_player(is_pitcher=True)
    assert player["movement"] == 90
    assert player["control"] == 50


def test_hitter_can_pitch(monkeypatch):
    def fake_randint(a, b):
        if (a, b) == (1, 1000):
            return 1
        if (a, b) == (10, 99):
            return 80
        return (a + b) // 2

    monkeypatch.setattr(pg.random, "randint", fake_randint)

    player = generate_player(is_pitcher=False, primary_position="1B")
    assert player["control"] == int(80 * 0.75)
    assert "P" in player["other_positions"]


def test_hitter_distribution_totals():
    weights = pg.HITTER_RATING_WEIGHTS["1B"]
    total = 500
    ratings = pg.distribute_rating_points(total, weights)
    assert sum(ratings.values()) == total


def test_pitcher_distribution_totals():
    weights = pg.PITCHER_RATING_WEIGHTS
    total = 480
    ratings = pg.distribute_rating_points(total, weights)
    assert sum(ratings.values()) == total


def test_skin_tone_distribution_matches_weights():
    random.seed(0)
    num_players = 600
    players = [generate_player(is_pitcher=False) for _ in range(num_players)]
    counts = Counter(p["skin_tone"] for p in players)
    total_weight = sum(pg.SKIN_TONE_WEIGHTS.values())
    for tone, weight in pg.SKIN_TONE_WEIGHTS.items():
        expected = weight / total_weight
        assert abs(counts[tone] / num_players - expected) < 0.05


def test_generate_pitches_counts_and_bonus(monkeypatch):
    base_total = 110

    def fake_randint(a, b):
        if (a, b) == (10 * len(pg.PITCH_LIST), 99 * len(pg.PITCH_LIST)):
            return base_total
        return (a + b) // 2

    monkeypatch.setattr(pg.random, "randint", fake_randint)
    monkeypatch.setattr(pg, "_weighted_choice", lambda w: next(iter(w)))

    ratings, _ = pg.generate_pitches("R", "overhand", age=25)

    assert sum(1 for r in ratings.values() if r > 0) == 3
    assert sum(ratings.values()) == base_total + 60
