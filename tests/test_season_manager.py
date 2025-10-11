import json
from playbalance.season_manager import SeasonManager, SeasonPhase


def test_cycle_phases(tmp_path):
    path = tmp_path / "state.json"
    manager = SeasonManager(path, enable_rollover=False)
    assert manager.phase == SeasonPhase.PRESEASON
    assert manager.advance_phase() == SeasonPhase.REGULAR_SEASON
    assert manager.advance_phase() == SeasonPhase.AMATEUR_DRAFT
    assert manager.advance_phase() == SeasonPhase.PLAYOFFS
    assert manager.advance_phase() == SeasonPhase.OFFSEASON
    assert manager.advance_phase() == SeasonPhase.PRESEASON


def test_state_persistence(tmp_path):
    path = tmp_path / "state.json"
    manager = SeasonManager(path, enable_rollover=False)
    manager.advance_phase()
    assert path.exists()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["phase"] == "REGULAR_SEASON"
    new_manager = SeasonManager(path, enable_rollover=False)
    assert new_manager.phase == SeasonPhase.REGULAR_SEASON


def test_phase_handlers(tmp_path):
    path = tmp_path / "state.json"
    manager = SeasonManager(path, enable_rollover=False)
    assert "Preseason" in manager.handle_phase()
    manager.advance_phase()
    assert "Regular Season" in manager.handle_phase()
    manager.advance_phase()
    assert "Amateur Draft" in manager.handle_phase()
    manager.advance_phase()
    assert "Playoffs" in manager.handle_phase()
    manager.advance_phase()
    assert "Offseason" in manager.handle_phase()
