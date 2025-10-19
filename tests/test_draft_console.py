import sys
import types

# Ensure fallback widgets are used if PyQt6 is unavailable
for mod in ("PyQt6", "PyQt6.QtWidgets", "PyQt6.QtCore", "PyQt6.QtGui"):
    sys.modules.setdefault(mod, types.ModuleType(mod))

from utils.exceptions import DraftRosterError
import ui.draft_console as console


class DummySeasonManager:
    def __init__(self):
        self.phase = None

    def save(self) -> None:
        pass


DummySeasonPhase = types.SimpleNamespace(REGULAR_SEASON=object())


def test_commit_to_rosters_keeps_compliance_messages(monkeypatch):
    dlg = console.DraftConsole.__new__(console.DraftConsole)
    dlg.year = 2025
    dlg.draft_date = "2025-07-15"
    dlg.assignment_summary = {}
    dlg.assignment_failures = []
    dlg.last_assignment_error = None

    summary = {
        "players_added": 0,
        "roster_assigned": 36,
        "failures": [],
        "compliance_issues": ["BUF: LOW roster exceeds limit"],
    }

    def fake_commit(year, season_date=None):
        raise DraftRosterError(summary["compliance_issues"], summary)

    mark_called = []

    monkeypatch.setattr(
        "services.draft_assignment.commit_draft_results", fake_commit
    )
    monkeypatch.setattr(console, "mark_draft_completed", lambda year: mark_called.append(year))
    monkeypatch.setattr("playbalance.season_manager.SeasonManager", DummySeasonManager)
    monkeypatch.setattr("playbalance.season_manager.SeasonPhase", DummySeasonPhase)
    monkeypatch.setattr(console, "log_news_event", lambda *a, **k: None)

    dlg._commit_to_rosters()

    assert dlg.assignment_summary["failures"] == []
    assert dlg.assignment_summary["compliance_issues"] == ["BUF: LOW roster exceeds limit"]
    assert dlg.assignment_failures == ["BUF: LOW roster exceeds limit"]
    assert mark_called == [2025]
