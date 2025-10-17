from __future__ import annotations

"""Helpers for retrieving the current NexGen BBPro version string."""

from functools import lru_cache
from pathlib import Path

from .path_utils import get_base_dir


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return the application version, falling back to ``'dev'`` if unknown."""

    base = get_base_dir()
    version_file = Path(base) / "VERSION"
    try:
        raw = version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "dev"
    return raw or "dev"


__all__ = ["get_version"]

