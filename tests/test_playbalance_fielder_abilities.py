from types import SimpleNamespace
import pytest

from playbalance import (
    reaction_delay,
    catch_chance,
    max_throw_distance,
    throw_speed,
    good_throw_chance,
    wild_pitch_catch_chance,
    should_chase_ball,
)


def make_cfg(**kwargs):
    return SimpleNamespace(**kwargs)


def test_reaction_delay():
    cfg = make_cfg(delayBaseCatcher=12, delayFAPctCatcher=-4)
    assert reaction_delay(cfg, "C", 50) == 10.0


def test_catch_chance_adjustments():
    cfg = make_cfg(
        catchBaseChance=90,
        catchFADiv=7,
        catchChanceDiving=-40,
        catchChanceLeaping=-15,
        catchChanceLessThan1Sec=-10,
        catchChancePerTenth=-1,
        catchChanceThirdBaseAdjust=0,
        automaticCatchDist=15,
    )
    # Diving 3B with 0.5s hang time and 20ft distance
    prob = catch_chance(cfg, "3B", fa=50, air_time=0.5, distance=20, diving=True)
    assert prob == pytest.approx(0.4214286, rel=1e-6)


def test_throwing_metrics():
    cfg = make_cfg(
        maxThrowDistBase=190,
        maxThrowDistASPct=100,
        throwSpeedIFBase=52,
        throwSpeedIFDistPct=3,
        throwSpeedIFASPct=0,
        throwSpeedIFMax=92,
        throwSpeedOFBase=52,
        throwSpeedOFDistPct=3,
        throwSpeedOFASPct=0,
        throwSpeedOFMax=92,
    )
    assert max_throw_distance(cfg, 50) == 240
    assert throw_speed(cfg, 150, 60) == pytest.approx(56.5)
    # Large distance capped at max speed for outfielders
    assert throw_speed(cfg, 2000, 60, outfielder=True) == 92


def test_throw_accuracy_and_wild_pitch():
    cfg = make_cfg(
        goodThrowBase=63,
        goodThrowFAPct=40,
        goodThrowChanceCenterField=-10,
        wildCatchChanceBase=85,
        wildCatchChanceFAPct=50,
        wildCatchChanceOppMod=-10,
        wildCatchChanceHighMod=-5,
    )
    # CF accuracy
    assert good_throw_chance(cfg, "CF", 80) == pytest.approx(0.85)
    # Wild pitch catch chance with cross-body adjustment
    assert wild_pitch_catch_chance(cfg, 20, cross_body=True) == pytest.approx(0.85)


def test_chase_decisions():
    cfg = make_cfg(
        infieldMaxChaseDist=50,
        pitcherMaxChaseDist=90,
        outfieldMinChaseDist=150,
    )
    assert should_chase_ball(cfg, "SS", 40) is True
    assert should_chase_ball(cfg, "P", 100) is False
    assert should_chase_ball(cfg, "CF", 120) is False
    assert should_chase_ball(cfg, "LF", 200) is True
