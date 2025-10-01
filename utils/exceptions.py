from __future__ import annotations

"""Shared exception types for cross-module use."""

from typing import Iterable


class DraftRosterError(RuntimeError):
    """Raised when drafted players could not be placed on required rosters."""

    def __init__(self, failures: Iterable[str] | None = None, summary: dict | None = None):
        self.failures = list(failures or [])
        self.summary = dict(summary or {})
        message = (
            "Draft assignments failed; resolve roster issues before resuming"
            " the season."
        )
        if self.failures:
            message += " " + " ".join(self.failures)
        super().__init__(message)


__all__ = ["DraftRosterError"]
