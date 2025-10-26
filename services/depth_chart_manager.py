"""Helpers that apply depth chart preferences to roster moves."""

from __future__ import annotations

from typing import Iterable, Set

from models.roster import Roster
from utils.depth_chart import depth_order_for_position, load_depth_chart


def promote_depth_chart_replacement(
    roster: Roster,
    position: str | None,
    *,
    exclude: Iterable[str] | None = None,
) -> bool:
    """Promote the next preferred backup for ``position`` if available.

    Returns ``True`` when a player from AAA/Low was promoted to the active
    roster, otherwise ``False`` so callers can fall back to generic logic.
    """

    team_id = getattr(roster, "team_id", None)
    if not team_id or not position:
        return False
    try:
        chart = load_depth_chart(team_id)
    except Exception:
        return False
    depth_order = depth_order_for_position(chart, position)
    if not depth_order:
        return False
    skip: Set[str] = {str(pid) for pid in (exclude or []) if pid}
    dl = set(getattr(roster, "dl", []) or [])
    ir = set(getattr(roster, "ir", []) or [])
    for pid in depth_order:
        if not pid or pid in skip or pid in dl or pid in ir:
            continue
        if pid in roster.act:
            # Already active; lineup handling will use preference order.
            continue
        if pid in roster.aaa:
            roster.aaa.remove(pid)
            roster.act.append(pid)
            return True
        if pid in roster.low:
            roster.low.remove(pid)
            roster.act.append(pid)
            return True
    return False


__all__ = ["promote_depth_chart_replacement"]
