import playbalance.playbalance_config as playbalance_config
from playbalance.playbalance_config import PlayBalanceConfig
from playbalance.simulation import GameSimulation, TeamState, BatterState
from tests.test_physics import make_player, make_pitcher, MockRandom
import pytest


def test_playbalance_config_defaults():
    cfg = PlayBalanceConfig.from_dict({})
    defaults = playbalance_config._DEFAULTS

    # Physics defaults
    assert cfg.speedBase == defaults["speedBase"]
    assert cfg.swingAngleTenthDegreesBase == defaults["swingAngleTenthDegreesBase"]
    assert cfg.exit_velo_base == defaults["exitVeloBase"]
    assert cfg.exit_velo_ph_pct == defaults["exitVeloPHPct"]
    assert cfg.exit_velo_power_pct == defaults["exitVeloPowerPct"]
    assert cfg.exit_velo_normal_pct == defaults["exitVeloNormalPct"]
    assert cfg.exit_velo_contact_pct == defaults["exitVeloContactPct"]
    assert cfg.vert_angle_gf_pct == defaults["vertAngleGFPct"]
    assert cfg.spray_angle_pl_pct == defaults["sprayAnglePLPct"]
    assert cfg.ground_ball_base_rate == defaults["groundBallBaseRate"]
    assert cfg.fly_ball_base_rate == defaults["flyBallBaseRate"]
    assert cfg.hit_prob_base == pytest.approx(defaults["hitProbBase"] * 0.1)
    assert cfg.foulPitchBasePct == defaults["foulPitchBasePct"]
    assert cfg.foulStrikeBasePct == defaults["foulStrikeBasePct"]
    assert cfg.foulContactTrendPct == defaults["foulContactTrendPct"]
    assert cfg.minMisreadContact == defaults["minMisreadContact"]

    # Pitcher AI defaults
    assert cfg.pitchRatVariationCount == defaults["pitchRatVariationCount"]
    assert cfg.pitchObj00CountEstablishWeight == defaults["pitchObj00CountEstablishWeight"]

    # Batter AI defaults
    assert cfg.sureStrikeDist == pytest.approx(defaults["sureStrikeDist"])
    assert cfg.lookPrimaryType00CountAdjust == defaults["lookPrimaryType00CountAdjust"]
    assert cfg.lookBestType30CountAdjust == defaults["lookBestType30CountAdjust"]


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


def test_get_uses_default(monkeypatch):
    monkeypatch.setitem(playbalance_config._DEFAULTS, "sampleKey", 99)
    cfg = PlayBalanceConfig.from_dict({})
    assert cfg.get("sampleKey") == 99


