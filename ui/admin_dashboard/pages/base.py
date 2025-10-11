"""Base classes for new admin dashboard pages."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QWidget

from ..context import DashboardContext


class DashboardPage(QWidget):
    """Skeleton QWidget with a lifecycle hook for the shared context."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._context: Optional[DashboardContext] = None

    @property
    def context(self) -> DashboardContext:
        if self._context is None:
            raise RuntimeError("DashboardContext not attached yet")
        return self._context

    def attach(self, context: DashboardContext) -> None:
        self._context = context
        self.on_attached()

    def on_attached(self) -> None:
        """Hook invoked once the shared context is available."""

    def refresh(self) -> None:  # pragma: no cover - UI hook
        """Optional hook for navigation controller to trigger reloads."""


__all__ = ["DashboardPage"]
