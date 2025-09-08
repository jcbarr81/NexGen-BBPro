from playbalance import load_config
from playbalance.defense import (
    bunt_charge_chance,
    hold_runner_chance,
    pickoff_chance,
    pitch_out_chance,
    pitch_around_chance,
    outfielder_position,
    fielder_template,
)


cfg = load_config()


def test_bunt_charge_chance_range():
    chance = bunt_charge_chance(
        cfg,
        "3B",
        fielder_fa=50,
        pitcher_fa=60,
        sac_chance=30,
        runner_on_first=True,
        runner_on_second=True,
    )
    assert 0.0 <= chance <= 1.0


def test_hold_runner_chance_increases_with_speed():
    slow = hold_runner_chance(cfg, runner_speed=20)
    fast = hold_runner_chance(cfg, runner_speed=40)
    assert slow <= fast <= 1.0


def test_pickoff_chance_range():
    chance = pickoff_chance(cfg, steal_chance=30, lead_level=2, pitches_since=0)
    assert 0.0 <= chance <= 1.0


def test_pitch_out_chance_thresholds():
    chance = pitch_out_chance(
        cfg,
        steal_chance=30,
        hit_run_chance=10,
        balls=0,
        inning=9,
        home_team=True,
    )
    assert 0.0 <= chance <= 1.0


def test_pitch_around_and_ibb_relationship():
    pa, ibb = pitch_around_chance(
        cfg,
        inning=9,
        batter_ph=80,
        on_deck_ph=40,
        batter_ch=70,
        on_deck_ch=50,
        ground_fly=40,
        outs=1,
        on_second_and_third=True,
    )
    assert 0.0 <= ibb <= pa <= 1.0


def test_outfielder_position_and_template():
    shift, depth = outfielder_position(cfg, pull_rating=90, power_rating=90)
    assert shift in (-2, -1, 0, 1, 2)
    assert depth in {"in", "normal", "back"}
    dist, angle = fielder_template(cfg, "normal", "1B")
    assert dist > 0
    assert -90 <= angle <= 90
