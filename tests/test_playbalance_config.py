import logic.playbalance_config as playbalance_config
from logic.playbalance_config import PlayBalanceConfig
from logic.simulation import GameSimulation, TeamState, BatterState
from tests.test_physics import make_player, make_pitcher, MockRandom


def test_playbalance_config_defaults():
    cfg = PlayBalanceConfig.from_dict({})

    # Physics defaults
    assert cfg.speedBase == 19
    assert cfg.swingAngleTenthDegreesBase == 44

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


def test_speedbase_override_affects_simulation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        playbalance_config, "_OVERRIDE_PATH", tmp_path / "overrides.json"
    )
    playbalance_config._DEFAULTS.clear()
    playbalance_config._DEFAULTS.update(playbalance_config._BASE_DEFAULTS)

    def advance_base(cfg: PlayBalanceConfig) -> int:
        batter = make_player("bat", ph=80)
        runner = make_player("run", sp=50)
        runner_state = BatterState(runner)
        home = TeamState(
            lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp1")]
        )
        away = TeamState(
            lineup=[batter], bench=[], pitchers=[make_pitcher("ap1")]
        )
        away.lineup_stats[runner.player_id] = runner_state
        away.bases[0] = runner_state
        sim = GameSimulation(home, away, cfg, MockRandom([0.0, 0.0, 0.9, 0.9]))
        sim.play_at_bat(away, home)
        if away.bases[2] is runner_state:
            return 3
        if away.bases[1] is runner_state:
            return 2
        return 1

    baseline = advance_base(PlayBalanceConfig())
    assert baseline == 2

    cfg = PlayBalanceConfig()
    cfg.speedBase = 30
    cfg.save_overrides()

    playbalance_config._DEFAULTS.clear()
    playbalance_config._DEFAULTS.update(playbalance_config._BASE_DEFAULTS)
    playbalance_config.PlayBalanceConfig.load_overrides()

    overridden = advance_base(PlayBalanceConfig())
    assert overridden == 3

    cfg.reset()
    reset = advance_base(PlayBalanceConfig())
    assert reset == baseline

