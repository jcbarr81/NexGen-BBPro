import pytest

from playbalance.simulation import BatterState
from playbalance.stats import compute_batting_derived


class DummyPlayer:
    pass


def test_pitches_per_pa():
    bs = BatterState(DummyPlayer())
    bs.pa = 100
    bs.pitches = 386
    derived = compute_batting_derived(bs)
    assert derived["p_pa"] == pytest.approx(3.86, abs=0.01)
