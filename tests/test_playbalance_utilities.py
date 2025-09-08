from types import SimpleNamespace
from random import seed

from playbalance import (
    combine_offense,
    combine_slugging,
    combine_defense,
    pct_modifier,
    adjustment,
    dice_roll,
    final_chance,
    GameState,
    PlayerState,
)


def test_rating_helpers_use_config():
    cfg = SimpleNamespace(
        offenseContactWt=1.0,
        offensePowerWt=0.0,
        offenseDisciplineWt=0.0,
        slugPowerWt=0.5,
        slugDisciplineWt=0.5,
        defenseFieldingWt=0.7,
        defenseArmWt=0.2,
        defenseRangeWt=0.1,
    )
    assert combine_offense(80, 20, 40, cfg) == 80
    assert combine_slugging(60, 40, cfg) == 50
    assert combine_defense(70, 50, 40, cfg) == 63


def test_probability_helpers():
    assert pct_modifier(50, 50) == 25
    assert adjustment(25, 10) == 35
    seed(1)
    assert dice_roll(2, 6) == 7
    assert final_chance(0.5, pct_mods=[200], adjusts=[0.1]) == 1.0


def test_state_tracking():
    gs = GameState(weather={"temperature": 70.0}, park_factors={"overall": 100.0})
    gs.record_pitch()
    assert gs.pitch_count == 1
    ps = PlayerState("Test")
    ps.fatigue = 5.0
    ps.stats["hr"] = 1
    assert ps.stats["hr"] == 1
