import pytest

from playbalance.simulation import BatterState
from playbalance.state import PitcherState
from playbalance.stats import compute_batting_rates, compute_pitching_rates


class DummyPlayer:
    pass


def test_called_third_strike_rate():
    batter = BatterState(DummyPlayer())
    batter.so = 100
    batter.so_looking = 23
    rates = compute_batting_rates(batter)
    assert rates["so_looking_pct"] == pytest.approx(0.23, abs=0.01)

    pitcher = PitcherState()
    pitcher.player = DummyPlayer()
    pitcher.so = 100
    pitcher.so_looking = 23
    rates_p = compute_pitching_rates(pitcher)
    assert rates_p["so_looking_pct"] == pytest.approx(0.23, abs=0.01)
