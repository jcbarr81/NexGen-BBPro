import json
from logic.season_manager import SeasonManager, SeasonPhase


def test_cycle_phases(tmp_path):
    path = tmp_path / "state.json"
    manager = SeasonManager(path)
    assert manager.phase == SeasonPhase.PRESEASON
    assert manager.advance_phase() == SeasonPhase.REGULAR_SEASON
    assert manager.advance_phase() == SeasonPhase.PLAYOFFS
    assert manager.advance_phase() == SeasonPhase.OFFSEASON
    assert manager.advance_phase() == SeasonPhase.PRESEASON


def test_state_persistence(tmp_path):
    path = tmp_path / "state.json"
    manager = SeasonManager(path)
    manager.advance_phase()
    assert path.exists()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["phase"] == "REGULAR_SEASON"
    new_manager = SeasonManager(path)
    assert new_manager.phase == SeasonPhase.REGULAR_SEASON
