import logic.playbalance_config as playbalance_config
from logic.playbalance_config import PlayBalanceConfig


def test_playbalance_config_defaults():
    cfg = PlayBalanceConfig.from_dict({})

    # Physics defaults
    assert cfg.speedBase == 19
    assert cfg.swingAngleTenthDegreesBase == 44

    # Pitcher AI defaults
    assert cfg.pitchRatVariationCount == 1
    assert cfg.pitchObj00CountEstablishWeight == 0

    # Batter AI defaults
    assert cfg.sureStrikeDist == 3
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
    cfg.save_overrides()

    playbalance_config._DEFAULTS.clear()
    playbalance_config._DEFAULTS.update(playbalance_config._BASE_DEFAULTS)
    playbalance_config.PlayBalanceConfig.load_overrides()

    cfg2 = PlayBalanceConfig()
    assert cfg2.speedBase == 42
    cfg.reset()


def test_reset_overrides(tmp_path, monkeypatch):
    monkeypatch.setattr(
        playbalance_config, "_OVERRIDE_PATH", tmp_path / "overrides.json"
    )
    playbalance_config._DEFAULTS.clear()
    playbalance_config._DEFAULTS.update(playbalance_config._BASE_DEFAULTS)

    cfg = PlayBalanceConfig()
    cfg.speedBase = 42
    cfg.save_overrides()
    assert playbalance_config._OVERRIDE_PATH.exists()

    cfg.reset()
    assert (
        playbalance_config._DEFAULTS["speedBase"]
        == playbalance_config._BASE_DEFAULTS["speedBase"]
    )
    assert not playbalance_config._OVERRIDE_PATH.exists()
