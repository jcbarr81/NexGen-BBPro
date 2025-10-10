"""Backward-compatible import shim for shared dashboard navigation helpers."""
from __future__ import annotations

from ui.dashboard_core.navigation import (
    NavigationController,
    PageFactory,
    PageRegistry,
)

__all__ = ["NavigationController", "PageFactory", "PageRegistry"]

