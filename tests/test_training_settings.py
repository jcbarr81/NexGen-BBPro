import pytest

from services import training_settings


def _setup_tmp_settings(tmp_path, monkeypatch):
    settings_path = tmp_path / "training_settings.json"
    monkeypatch.setattr(training_settings, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(training_settings, "_resolve_league_id", lambda: "test-league")
    return settings_path


def test_training_settings_round_trip(tmp_path, monkeypatch) -> None:
    _setup_tmp_settings(tmp_path, monkeypatch)

    settings = training_settings.load_training_settings()
    assert settings.defaults.hitters == training_settings.DEFAULT_HITTER_ALLOCATIONS
    assert settings.team_overrides == {}

    hitters = {
        "contact": 25,
        "power": 25,
        "speed": 20,
        "discipline": 15,
        "defense": 15,
    }
    pitchers = {
        "command": 30,
        "movement": 15,
        "stamina": 20,
        "velocity": 20,
        "hold": 5,
        "pitch_lab": 10,
    }

    training_settings.update_league_training_defaults(hitters, pitchers)
    updated = training_settings.load_training_settings()
    assert updated.defaults.hitters["contact"] == 25
    assert updated.defaults.pitchers["command"] == 30

    team_weights = training_settings.set_team_training_weights("ABC", hitters, pitchers)
    assert team_weights.hitters["speed"] == 20

    reloaded = training_settings.load_training_settings()
    assert "ABC" in reloaded.team_overrides
    assert reloaded.for_team("ABC").hitters["power"] == 25


def test_training_settings_validation(tmp_path, monkeypatch) -> None:
    _setup_tmp_settings(tmp_path, monkeypatch)

    bad_hitters = {
        "contact": 100,
        "power": 0,
        "speed": 0,
        "discipline": 0,
        "defense": 0,
    }
    pitchers = training_settings.DEFAULT_PITCHER_ALLOCATIONS

    with pytest.raises(ValueError):
        training_settings.set_team_training_weights("ERR", bad_hitters, pitchers)
