"""Utilities for inferring player ethnicity from names."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple

_LOOKUP: Dict[Tuple[str, str], str] = {}
_FIRST_LOOKUP: Dict[str, str] = {}
_LAST_LOOKUP: Dict[str, str] = {}
_LOADED = False


def _load_lookup() -> None:
    """Load ethnicity lookup data from CSV into memory."""
    global _LOADED
    if _LOADED:
        return
    csv_path = Path(__file__).resolve().parent.parent / "data" / "ethnicity_lookup.csv"
    try:
        with csv_path.open(newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                first = row.get("first_name", "").strip().lower()
                last = row.get("last_name", "").strip().lower()
                ethnicity = row.get("ethnicity", "").strip()
                if first and last:
                    _LOOKUP[(first, last)] = ethnicity
                if first:
                    _FIRST_LOOKUP[first] = ethnicity
                if last:
                    _LAST_LOOKUP[last] = ethnicity
    finally:
        _LOADED = True


def infer_ethnicity(first_name: str, last_name: str) -> str:
    """Infer a player's ethnicity.

    The function uses a simple name lookup to return categories compatible
    with Icons8's avatar generation API. If the name is not found, it
    returns ``"unknown"``.

    Args:
        first_name: The player's first name.
        last_name: The player's last name.

    Returns:
        The inferred ethnicity string or ``"unknown"`` when no match is
        found.
    """

    _load_lookup()
    fn = first_name.strip().lower()
    ln = last_name.strip().lower()
    return _LOOKUP.get((fn, ln)) or _FIRST_LOOKUP.get(fn) or _LAST_LOOKUP.get(ln) or "unknown"


__all__ = ["infer_ethnicity"]
