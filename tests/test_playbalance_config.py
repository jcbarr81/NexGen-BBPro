import logic.playbalance_config as playbalance_config
from logic.playbalance_config import PlayBalanceConfig
from logic.simulation import GameSimulation, TeamState, BatterState
from tests.test_physics import make_player, make_pitcher, MockRandom
import pytest


def test_playbalance_config_defaults():
    cfg = PlayBalanceConfig.from_dict({})

    # Physics defaults
    assert cfg.speedBase == 19
    assert cfg.swingAngleTenthDegreesBase == 44
    assert cfg.exit_velo_base == 0
    assert cfg.exit_velo_ph_pct == 0
    assert cfg.exit_velo_power_pct == 100
    assert cfg.exit_velo_normal_pct == 100
    assert cfg.exit_velo_contact_pct == 100
    assert cfg.vert_angle_gf_pct == 0
    assert cfg.spray_angle_pl_pct == 0
    assert cfg.ground_ball_base_rate == 45
    assert cfg.fly_ball_base_rate == 55
    assert cfg.hit_prob_base == pytest.approx(0.02)
    assert cfg.foulPitchBasePct == 18.3
    assert cfg.foulStrikeBasePct == 31
    assert cfg.foulContactTrendPct == 2.0
    assert cfg.minMisreadContact == 0.5

    # Pitcher AI defaults
    assert cfg.pitchRatVariationCount == 1
    assert cfg.pitchObj00CountEstablishWeight == 0

    # Batter AI defaults
    assert cfg.sureStrikeDist == 4
    assert cfg.lookPrimaryType00CountAdjust == 0
    assert cfg.lookBestType30CountAdjust == 15


def test_save_and_load_overrides(tmp_path, monkeypatch):
    monkeypatch.setattr(
        playbalance_config, "_OVERRIDE_PATH", tmp_path / "overrides.json"
    )
    playbalance_config._DEFAULTS.clear()
    playbalance_config._DEFAULTS.update(playbalance_config._BASE_DEFAULTS)

    cfg = PlayBalanceConfig()
    cfg.speedBase = 42
    cfg.exitVeloBase = 99
    cfg.save_overrides()

    playbalance_config._DEFAULTS.clear()
    playbalance_config._DEFAULTS.update(playbalance_config._BASE_DEFAULTS)
    playbalance_config.PlayBalanceConfig.load_overrides()

    cfg2 = PlayBalanceConfig()
    assert cfg2.speedBase == 42
    assert cfg2.exit_velo_base == 99
    cfg.reset()


def test_reset_overrides(tmp_path, monkeypatch):
    monkeypatch.setattr(
        playbalance_config, "_OVERRIDE_PATH", tmp_path / "overrides.json"
    )
    playbalance_config._DEFAULTS.clear()
    playbalance_config._DEFAULTS.update(playbalance_config._BASE_DEFAULTS)

    cfg = PlayBalanceConfig()
    cfg.speedBase = 42
    cfg.exitVeloBase = 99
    cfg.save_overrides()
    assert playbalance_config._OVERRIDE_PATH.exists()

    cfg.reset()
    assert (
        playbalance_config._DEFAULTS["speedBase"]
        == playbalance_config._BASE_DEFAULTS["speedBase"]
    )
    assert (
        playbalance_config._DEFAULTS["exitVeloBase"]
        == playbalance_config._BASE_DEFAULTS["exitVeloBase"]
    )
    assert not playbalance_config._OVERRIDE_PATH.exists()


