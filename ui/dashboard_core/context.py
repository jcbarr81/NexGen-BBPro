"""Shared context helpers for dashboard-style windows."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Optional

Worker = Callable[[Callable[[], Any]], Any]
ToastFn = Callable[[str, str], None]
CleanupFn = Callable[[Callable[[], None]], None]


@dataclass(frozen=True)
class DashboardContext:
    """Lightweight dependency bundle for dashboard pages/actions."""

    base_path: Path
    run_async: Worker
    show_toast: Optional[ToastFn] = None
    register_cleanup: Optional[CleanupFn] = None

    def with_overrides(self, **changes: Any) -> "DashboardContext":
        """Return a cloned context with updated attributes."""
        return replace(self, **changes)


__all__ = ["DashboardContext", "Worker", "ToastFn", "CleanupFn"]

