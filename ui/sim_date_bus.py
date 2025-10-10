from __future__ import annotations

"""Lightweight application-wide broadcast for simulation date changes."""

from typing import Any, Callable, List, Optional

try:  # pragma: no cover - prefer real Qt when available
    from PyQt6.QtCore import QObject, pyqtSignal  # type: ignore
except Exception:  # pragma: no cover - fallback used in headless tests

    class QObject:  # type: ignore
        """Minimal stub matching the Qt API used in tests."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__()

    class _DummySignal:
        def __init__(self) -> None:
            self._subscribers: List[Callable[[Any], None]] = []

        def connect(self, callback: Callable[[Any], None]) -> None:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

        def disconnect(self, callback: Callable[[Any], None]) -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        def emit(self, value: Any = None) -> None:
            for cb in list(self._subscribers):
                try:
                    cb(value)
                except Exception:
                    pass

    def pyqtSignal(*_args: Any, **_kwargs: Any) -> _DummySignal:  # type: ignore
        return _DummySignal()


class _SimDateBus(QObject):
    """Singleton Qt object that emits when the sim date advances."""

    dateChanged = pyqtSignal(object)


_BUS: Optional[_SimDateBus] = None


def sim_date_bus() -> _SimDateBus:
    """Return the global simulation-date bus."""

    global _BUS
    if _BUS is None:
        _BUS = _SimDateBus()
    return _BUS


def notify_sim_date_changed(value: str | None) -> None:
    """Emit a notification that the simulation date changed to *value*."""

    bus = sim_date_bus()
    try:
        bus.dateChanged.emit(value)
    except Exception:
        # Fallback stubs already swallow exceptions independently
        pass


__all__ = ["sim_date_bus", "notify_sim_date_changed"]
