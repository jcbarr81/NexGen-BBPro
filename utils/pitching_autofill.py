"""Utilities for assigning pitchers to staff roles.

This module provides logic used by the ``PitchingEditor`` UI to automatically
assign available pitchers to staff roles in a sensible manner.  Starters are
chosen for the rotation before relievers, and relievers are distributed to the
bullpen with closers favoring low endurance arms.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from .pitcher_role import get_role

# Type aliases for clarity
PlayerEntry = Tuple[str, dict]
Assignments = Dict[str, str]


def autofill_pitching_staff(players: Iterable[PlayerEntry]) -> Assignments:
    """Return a mapping of pitching roles to player IDs.

    Parameters
    ----------
    players:
        An iterable of ``(player_id, data)`` pairs where ``data`` is a mapping
        containing at least ``endurance`` and attributes usable by
        :func:`utils.pitcher_role.get_role`.

    The algorithm prefers starting pitchers (``SP``) for the rotation.  If
    there are not enough starters, the highest-endurance relievers are used to
    fill any remaining rotation spots.  Bullpen roles are then assigned using
    the remaining relievers, with the long reliever getting the highest
    endurance and the closer getting the lowest endurance.
    """

    # Separate starters and relievers, capturing endurance as an int
    sps: list[tuple[str, int]] = []
    rps: list[tuple[str, int]] = []
    for pid, pdata in players:
        role = get_role(pdata)
        if not role:
            continue
        try:
            endurance = int(pdata.get("endurance", 0))
        except (TypeError, ValueError):
            endurance = 0
        if role == "SP":
            sps.append((pid, endurance))
        else:
            rps.append((pid, endurance))

    # Order by endurance descending for easier selection
    sps.sort(key=lambda x: x[1], reverse=True)
    rps.sort(key=lambda x: x[1], reverse=True)

    # Ensure the same pitcher cannot be assigned to multiple roles, even if
    # duplicated in the input (e.g., bad roster data).
    assigned: set[str] = set()

    def pop_next(seq: list[tuple[str, int]]) -> str | None:
        while seq:
            pid, _ = seq.pop(0)
            if pid in assigned:
                continue
            assigned.add(pid)
            return pid
        return None

    def pop_next_low(seq: list[tuple[str, int]]) -> str | None:
        while seq:
            pid, _ = seq.pop(-1)
            if pid in assigned:
                continue
            assigned.add(pid)
            return pid
        return None

    assignment: Assignments = {}

    # Fill the starting rotation (SP1-SP5)
    for i in range(5):
        pid = pop_next(sps)
        if pid is None:
            # Fall back to highest-endurance reliever if short on starters
            pid = pop_next(rps)
        if pid is None:
            break
        assignment[f"SP{i + 1}"] = pid

    # Bullpen roles use remaining relievers (unique by pid).
    pid = pop_next(rps)
    if pid is not None:
        assignment["LR"] = pid  # Long reliever prefers high endurance
    pid = pop_next(rps)
    if pid is not None:
        assignment["MR"] = pid  # Middle reliever
    pid = pop_next(rps)
    if pid is not None:
        assignment["SU"] = pid  # Setup
    pid = pop_next_low(rps)
    if pid is not None:
        assignment["CL"] = pid  # Closer prefers low endurance

    return assignment
