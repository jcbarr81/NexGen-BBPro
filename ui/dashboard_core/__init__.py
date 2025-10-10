"""Shared dashboard infrastructure used by admin and owner UIs."""
from __future__ import annotations

from .context import DashboardContext, Worker, ToastFn, CleanupFn
from .navigation import NavigationController, PageRegistry, PageFactory

__all__ = [
    "DashboardContext",
    "Worker",
    "ToastFn",
    "CleanupFn",
    "NavigationController",
    "PageRegistry",
    "PageFactory",
]

