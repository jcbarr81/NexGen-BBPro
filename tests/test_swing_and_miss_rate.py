import pytest

from playbalance.state import PitcherState
from playbalance.stats import compute_pitching_rates


class DummyPitcher:
    pass


def test_swing_and_miss_rate():
    ps = PitcherState()
    ps.player = DummyPitcher()
    ps.pitches_thrown = 100
    ps.zone_swings = 25
    ps.zone_contacts = 18
    ps.o_zone_swings = 15
    ps.o_zone_contacts = 11
    rates = compute_pitching_rates(ps)
    assert rates["swstr_pct"] == pytest.approx(0.11, abs=0.01)
