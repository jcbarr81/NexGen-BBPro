"""Compatibility shim exposing the legacy admin dashboard.

All existing entry points (import ui.admin_dashboard) continue to work
by re-exporting the monolithic implementation from
`ui._admin_dashboard_legacy`. Future iterations will replace these
re-exports with modular components.
"""
from __future__ import annotations

from .. import _admin_dashboard_legacy as _legacy
from .._admin_dashboard_legacy import *  # noqa: F401,F403
from .main_window import MainWindow as _ModularMainWindow

LegacyMainWindow = _legacy.MainWindow
MainWindow = _ModularMainWindow

_exports = getattr(
    _legacy,
    "__all__",
    [name for name in dir(_legacy) if not name.startswith("_")],
)
_exports.extend(["MainWindow", "LegacyMainWindow"])
__all__ = sorted(set(_exports))
