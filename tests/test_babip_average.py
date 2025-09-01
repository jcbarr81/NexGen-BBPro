import pytest

from logic.simulation import BatterState
from logic.stats import compute_batting_rates


class DummyPlayer:
    pass


def test_babip_average():
    bs = BatterState(DummyPlayer())
    bs.ab = 500
    bs.h = 132
    bs.hr = 20
    bs.so = 100
    bs.sf = 5
    rates = compute_batting_rates(bs)
    assert rates["babip"] == pytest.approx(0.291, abs=0.001)
