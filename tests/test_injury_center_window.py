from __future__ import annotations

def test_import_injury_center_window_headless():
    from ui.injury_center_window import InjuryCenterWindow  # noqa: F401
    assert InjuryCenterWindow is not None

