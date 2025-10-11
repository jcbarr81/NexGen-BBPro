import pytest

from playbalance.simulation import BatterState
from playbalance.stats import compute_batting_rates


class DummyPlayer:
    pass


def test_babip_average():
    bs = BatterState(DummyPlayer())
    # Values picked to produce a league-average BABIP near .300
    bs.ab = 490
    bs.h = 134
    bs.hr = 20
    bs.so = 90
    bs.sf = 0
    rates = compute_batting_rates(bs)
    assert rates["babip"] == pytest.approx(0.300, abs=0.001)
