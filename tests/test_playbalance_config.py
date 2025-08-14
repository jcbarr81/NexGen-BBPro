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
