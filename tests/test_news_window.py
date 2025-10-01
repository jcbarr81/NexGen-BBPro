from __future__ import annotations

def test_import_news_window_headless():
    from ui.news_window import NewsWindow  # noqa: F401
    assert NewsWindow is not None

