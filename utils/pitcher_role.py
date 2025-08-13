"""Utilities for determining pitcher roles."""

from __future__ import annotations
from typing import Any

ENDURANCE_THRESHOLD = 55

def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Return attribute or dict key value from *obj* if present."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)

def get_role(pitcher: Any) -> str:
    """Return the role for *pitcher* as ``"SP"`` or ``"RP"``.

    The role is determined in the following order:
    1. Use the stored ``role`` attribute or key if it is ``"SP"`` or ``"RP"``.
    2. Fall back to ``primary_position`` if it is ``"SP"`` or ``"RP"``.
    3. Derive from ``endurance`` using ``ENDURANCE_THRESHOLD``.
       Pitchers with endurance greater than the threshold are considered
       starters, otherwise relievers.

    If *pitcher* does not appear to be a pitcher, an empty string is
    returned.  The function accepts either objects with attributes or
    dictionaries with matching keys.
    """

    role = str(_get_attr(pitcher, "role", "")).upper()
    if role in {"SP", "RP"}:
        return role

    primary = str(_get_attr(pitcher, "primary_position", "")).upper()
    if primary in {"SP", "RP"}:
        return primary
    if primary and primary not in {"SP", "RP", "P"}:
        return ""

    endurance = _get_attr(pitcher, "endurance")
    try:
        endurance = int(endurance)
    except (TypeError, ValueError):
        endurance = None

    if endurance is None:
        return ""

    return "SP" if endurance > ENDURANCE_THRESHOLD else "RP"
