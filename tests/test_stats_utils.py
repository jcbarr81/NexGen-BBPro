from tests.test_simulation import make_player
from logic.simulation import BatterState
from logic.stats import compute_batting_derived, compute_batting_rates
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
