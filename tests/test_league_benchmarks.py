import pytest

from logic.playbalance_config import PlayBalanceConfig
from logic.sim_config import apply_league_benchmarks


def test_apply_league_benchmarks():
    cfg = PlayBalanceConfig.from_dict({"hitHRProb": 5})
    benchmarks = {
        # Updated MLB benchmark BABIP
        "babip": 0.300,
        "pitches_put_in_play_pct": 0.175,
        "pitches_per_pa": 3.86,
        "bip_gb_pct": 0.44,
        "bip_fb_pct": 0.35,
        "bip_ld_pct": 0.21,
    }
    apply_league_benchmarks(cfg, benchmarks)
    assert cfg.hitProbBase == pytest.approx(0.300 / 0.95, abs=0.0001)
    assert cfg.ballInPlayPitchPct == 18
    assert cfg.swingProbScale == pytest.approx(1.04, abs=0.001)
    assert cfg.groundOutProb == pytest.approx(0.189, abs=0.001)
    assert cfg.lineOutProb == pytest.approx(0.08, abs=0.001)
    assert cfg.flyOutProb == pytest.approx(0.214, abs=0.001)
