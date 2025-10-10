"""Backward-compatible import shim for shared dashboard context."""
from __future__ import annotations

from ui.dashboard_core.context import DashboardContext, Worker, ToastFn, CleanupFn

__all__ = ["DashboardContext", "Worker", "ToastFn", "CleanupFn"]

