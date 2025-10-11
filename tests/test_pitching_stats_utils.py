from tests.test_simulation import make_pitcher
from playbalance.state import PitcherState
from playbalance.stats import compute_pitching_derived, compute_pitching_rates
from pytest import approx


def test_pitching_stat_helpers():
    pitcher = make_pitcher("p")
    stats = PitcherState()
    stats.player = pitcher
    stats.gs = 1
    stats.gf = 1
    stats.outs = 27
    stats.r = 0
    stats.er = 0
    stats.h = 3
    stats.hr = 1
    stats.bb = 1
    stats.so = 9
    stats.bf = 27
    stats.hbp = 0
    stats.first_pitch_strikes = 20
    stats.pitches_thrown = 90
    stats.zone_pitches = 50
    stats.o_zone_pitches = 40
    stats.zone_swings = 30
    stats.zone_contacts = 25
    stats.o_zone_swings = 10
    stats.o_zone_contacts = 5

    derived = compute_pitching_derived(stats)
    assert derived["ip"] == approx(9.0)
    assert derived["cg"] == 1
    assert derived["sho"] == 1
    assert derived["qs"] == 1
    assert derived["k_minus_bb"] == 8

    rates = compute_pitching_rates(stats)
    assert rates["h9"] == approx(3.0)
    assert rates["hr9"] == approx(1.0)
    assert rates["k9"] == approx(9.0)
    assert rates["bb9"] == approx(1.0)
    assert rates["era"] == approx(0.0)
    assert rates["whip"] == approx(4 / 9)
    assert rates["k_bb"] == approx(9.0)
    assert rates["fip"] == approx(2.978, rel=1e-3)
    assert rates["lob_pct"] == approx(4 / 2.6)
    assert rates["fps_pct"] == approx(20 / 27)
    assert rates["zone_pct"] == approx(50 / 90)
    assert rates["z_swing_pct"] == approx(30 / 50)
    assert rates["z_contact_pct"] == approx(25 / 30)
    assert rates["ozone_pct"] == approx(40 / 90)
    assert rates["ozone_swing_pct"] == approx(10 / 40)
    assert rates["ozone_contact_pct"] == approx(5 / 10)

