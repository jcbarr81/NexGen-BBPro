from tests.test_simulation import make_player
from tests.test_simulation import make_player
from playbalance.simulation import BatterState, FieldingState
from playbalance.stats import (
    compute_batting_derived,
    compute_batting_rates,
    compute_fielding_derived,
    compute_fielding_rates,
)
from pytest import approx


def test_batting_stat_helpers():
    player = make_player("p")
    stats = BatterState(player)
    stats.pa = 5
    stats.ab = 4
    stats.h = 2
    stats.b1 = 1
    stats.b2 = 1
    stats.hr = 0
    stats.bb = 1
    stats.hbp = 0
    stats.sf = 0
    stats.so = 1
    stats.sb = 1
    stats.cs = 1
    stats.pitches = 20
    stats.lob = 2

    derived = compute_batting_derived(stats)
    assert derived["tb"] == 3
    assert derived["xbh"] == 1
    assert derived["lob"] == 2
    assert derived["p_pa"] == approx(4.0)

    rates = compute_batting_rates(stats)
    assert rates["avg"] == approx(0.5)
    assert rates["obp"] == approx(0.6)
    assert rates["slg"] == approx(0.75)
    assert rates["ops"] == approx(1.35)
    assert rates["iso"] == approx(0.25)
    assert rates["babip"] == approx(2 / 3)
    assert rates["bb_pct"] == approx(0.2)
    assert rates["k_pct"] == approx(0.2)
    assert rates["bb_k"] == approx(1.0)
    assert rates["sb_pct"] == approx(0.5)


def test_fielding_stat_helpers():
    player = make_player("p")
    player.primary_position = "C"
    stats = FieldingState(player)
    stats.g = 1
    stats.gs = 1
    stats.po = 1
    stats.a = 1
    stats.cs = 1
    stats.sba = 1

    derived = compute_fielding_derived(stats)
    assert derived["tc"] == 2
    assert derived["of_a"] == 0

    rates = compute_fielding_rates(stats)
    assert rates["fpct"] == approx(1.0)
    assert rates["rf9"] == approx(2.0)
    assert rates["rfg"] == approx(2.0)
    assert rates["cs_pct"] == approx(1.0)
    assert rates["pb_g"] == approx(0.0)
