"""Modular admin dashboard main window."""
from __future__ import annotations

from typing import Callable, Dict

from PyQt6.QtWidgets import QWidget

from .. import _admin_dashboard_legacy as _legacy
from .context import DashboardContext
from .navigation import NavigationController, PageRegistry


class MainWindow(_legacy.MainWindow):
    """Dashboard window backed by the modular navigation primitives."""

    def __init__(self) -> None:
        self._page_registry = PageRegistry()
        self._navigation = NavigationController(self._page_registry)
        super().__init__()
        pages = getattr(self, "pages", {})
        if pages:
            try:
                self._navigation.set_current(next(iter(pages.keys())))
            except (KeyError, StopIteration):
                pass

    @property
    def context(self) -> DashboardContext:
        """Expose the shared dashboard context."""

        return self._context

    def _page_factories(self) -> Dict[str, Callable[[DashboardContext], QWidget]]:
        factories = super()._page_factories()
        self._page_registry = PageRegistry()
        if hasattr(self, "_navigation"):
            self._navigation.bind_registry(self._page_registry)
        for key, factory in factories.items():
            self._page_registry.register(key, factory)
        return factories

    def _go(self, key: str) -> None:
        try:
            self._navigation.set_current(key)
        except KeyError:
            pass
        super()._go(key)


__all__ = ["MainWindow"]



