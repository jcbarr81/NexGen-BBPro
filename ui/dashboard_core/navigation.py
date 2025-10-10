"""Navigation scaffolding shared across dashboard windows."""
from __future__ import annotations

from collections import OrderedDict
from typing import Callable, Dict, Iterable

from PyQt6.QtWidgets import QWidget

from .context import DashboardContext

PageFactory = Callable[[DashboardContext], QWidget]


class PageRegistry:
    """Registry mapping navigation keys to page factories."""

    def __init__(self) -> None:
        self._factories: Dict[str, PageFactory] = OrderedDict()

    def register(self, key: str, factory: PageFactory) -> None:
        if key in self._factories:
            raise KeyError(f"Page '{key}' already registered")
        self._factories[key] = factory

    def keys(self) -> Iterable[str]:
        return self._factories.keys()

    def build(self, key: str, context: DashboardContext) -> QWidget:
        return self._factories[key](context)


class NavigationController:
    """Coordinates nav button state and stacked page selection."""

    def __init__(self, registry: PageRegistry) -> None:
        self._registry = registry
        self._current_key: str | None = None
        self._listeners: list[Callable[[str | None], None]] = []

    @property
    def current_key(self) -> str | None:
        return self._current_key

    def add_listener(self, callback: Callable[[str | None], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str | None], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def bind_registry(self, registry: PageRegistry) -> None:
        self._registry = registry
        if self._current_key not in registry.keys():
            self._current_key = None
            self._emit()

    def set_current(self, key: str) -> None:
        if key not in self._registry.keys():
            raise KeyError(f"Unknown page '{key}'")
        if self._current_key == key:
            self._emit()
            return
        self._current_key = key
        self._emit()

    def create_page(self, key: str, context: DashboardContext) -> QWidget:
        page = self._registry.build(key, context)
        self._current_key = key
        self._emit()
        return page

    def _emit(self) -> None:
        for listener in list(self._listeners):
            try:
                listener(self._current_key)
            except Exception:
                pass


__all__ = ["PageRegistry", "NavigationController", "PageFactory"]

