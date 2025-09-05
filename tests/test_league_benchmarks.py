import pytest

from logic.playbalance_config import PlayBalanceConfig
from scripts.simulate_season_avg import apply_league_benchmarks


def test_apply_league_benchmarks():
    cfg = PlayBalanceConfig.from_dict({"hitHRProb": 5})
    benchmarks = {
        "babip": 0.291,
        "pitches_put_in_play_pct": 0.175,
        "pitches_per_pa": 3.86,
    }
    apply_league_benchmarks(cfg, benchmarks)
    assert cfg.hitProbBase == pytest.approx(0.291 / 0.95 * 1.25, abs=0.0001)
    assert cfg.ballInPlayPitchPct == 18
    assert cfg.swingProbScale == pytest.approx(1.04, abs=0.001)
