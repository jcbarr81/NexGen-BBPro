from __future__ import annotations

from pathlib import Path
import sys


def get_base_dir() -> Path:
    """Return project root or PyInstaller's temporary directory."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
