from __future__ import annotations

def test_import_free_agency_window_headless():
    # Ensure the window module imports and exposes the class, even headless
    from ui.free_agency_window import FreeAgencyWindow  # noqa: F401
    assert FreeAgencyWindow is not None

