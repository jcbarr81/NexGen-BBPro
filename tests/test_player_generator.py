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
    monkeypatch.setattr(pg, "_adjust_endurance", lambda e: e)

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
    monkeypatch.setattr(pg, "_adjust_endurance", lambda e: e)

    player = generate_player(is_pitcher=True)
    assert player["endurance"] == 55
    assert player["role"] == "RP"


def test_pitcher_can_hit(monkeypatch):
    def fake_add_hitting(player, age, allocation=0.75):
        rating = int(80 * allocation)
        player.update(
            {
                "ch": rating,
                "pot_ch": pg.bounded_potential(rating, age),
            }
        )

    monkeypatch.setattr(pg, "_maybe_add_hitting", fake_add_hitting)
    # Ensure a younger age so potential is not reduced.
    def fixed_birthdate(age_range=None, player_type="fictional"):
        from datetime import date, timedelta
        age = 25
        return (date.today() - timedelta(days=age * 365), age)

    monkeypatch.setattr(pg, "generate_birthdate", fixed_birthdate)

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


def test_hitter_modifier_ranges(monkeypatch):
    monkeypatch.setattr(pg, "_maybe_add_pitching", lambda *args, **kwargs: None)
    player = generate_player(is_pitcher=False)
    assert 40 <= player["mo"] <= 60
    assert 35 <= player["gf"] <= 65
    assert 40 <= player["cl"] <= 60
    assert 40 <= player["hm"] <= 60
    assert 40 <= player["sc"] <= 60
    assert 40 <= player["pl"] <= 60
    if player["bats"] == "L":
        assert 30 <= player["vl"] <= 60
    elif player["bats"] == "R":
        assert 40 <= player["vl"] <= 70
    else:
        assert 35 <= player["vl"] <= 65


def test_pitcher_modifier_ranges(monkeypatch):
    monkeypatch.setattr(pg, "_maybe_add_hitting", lambda *args, **kwargs: None)
    player = generate_player(is_pitcher=True)
    assert 40 <= player["mo"] <= 60
    assert 35 <= player["gf"] <= 65
    assert 40 <= player["cl"] <= 60
    assert 40 <= player["hm"] <= 60
    assert 40 <= player["pl"] <= 60
    if player["throws"] == "L":
        assert 40 <= player["vl"] <= 70
    else:
        assert 30 <= player["vl"] <= 60


def test_skin_tone_distribution_matches_weights():
    random.seed(0)
    num_players = 600
    players = [generate_player(is_pitcher=False) for _ in range(num_players)]
    counts = Counter(p["skin_tone"] for p in players)
    total_weight = sum(pg.SKIN_TONE_WEIGHTS.values())
    for tone, weight in pg.SKIN_TONE_WEIGHTS.items():
        expected = weight / total_weight
        assert abs(counts[tone] / num_players - expected) < 0.05


def test_generate_pitches_counts_and_bounds(monkeypatch):
    def fake_randint(a, b):
        if (a, b) == (2, 5):
            return 3  # number of pitches
        if (a, b) == (40, 99):
            return 80  # fastball rating
        if (a, b) == (20, 95):
            return 50  # other pitch ratings
        return (a + b) // 2

    monkeypatch.setattr(pg.random, "randint", fake_randint)
    monkeypatch.setattr(pg.random, "choices", lambda seq, weights=None: [seq[0]])

    ratings, _ = pg.generate_pitches("R", "overhand", age=25)

    assert ratings["fb"] == 80
    assert ratings["si"] == 50
    assert ratings["cu"] == 50
    assert sum(1 for r in ratings.values() if r > 0) == 3
    assert all(0 <= r <= 99 for r in ratings.values())


def test_endurance_adjustment_adds(monkeypatch):
    def fake_randint(a, b):
        if (a, b) == (1, 100):
            return 10  # trigger modification
        if (a, b) == (1, 20):
            return 5   # delta
        return a

    monkeypatch.setattr(pg.random, "randint", fake_randint)
    monkeypatch.setattr(pg.random, "choice", lambda seq: 1)

    assert pg._adjust_endurance(40) == 45


def test_endurance_adjustment_subtracts(monkeypatch):
    def fake_randint(a, b):
        if (a, b) == (1, 100):
            return 10  # trigger modification
        if (a, b) == (1, 20):
            return 5   # delta
        return a

    monkeypatch.setattr(pg.random, "randint", fake_randint)
    monkeypatch.setattr(pg.random, "choice", lambda seq: -1)

    assert pg._adjust_endurance(40) == 35


def test_fielding_potentials_for_unassigned_positions(monkeypatch):
    monkeypatch.setattr(pg, "assign_secondary_positions", lambda primary: [])
    player = generate_player(is_pitcher=False, primary_position="1B")
    pot_fielding = player["pot_fielding"]
    assert player["primary_position"] not in pot_fielding
    assert pot_fielding["2B"] == 20
    assert len(pot_fielding) > 0
