from pytest import approx

from playbalance.state import PitcherState
from playbalance.stats import compute_pitching_rates


def test_o_swing_and_zone_pct():
    ps = PitcherState()
    ps.record_pitch(in_zone=True, swung=False, contact=False)
    ps.record_pitch(in_zone=False, swung=True, contact=False)
    ps.record_pitch(in_zone=False, swung=False, contact=False)
    ps.pitches_thrown = ps.zone_pitches + ps.o_zone_pitches
    rates = compute_pitching_rates(ps)
    assert ps.o_zone_pitches == 2
    assert rates["ozone_swing_pct"] == approx(1 / 2)
    assert rates["z_swing_pct"] == approx(0)
    assert rates["zone_pct"] == approx(1 / 3)
