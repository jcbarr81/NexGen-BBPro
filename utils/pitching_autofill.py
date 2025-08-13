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

    assignment: Assignments = {}

    # Fill the starting rotation (SP1-SP5)
    for i in range(5):
        if sps:
            pid, _ = sps.pop(0)
        elif rps:
            # Fall back to highest-endurance reliever if short on starters
            pid, _ = rps.pop(0)
        else:
            break
        assignment[f"SP{i + 1}"] = pid

    # Bullpen roles use remaining relievers.
    if rps:
        pid, _ = rps.pop(0)
        assignment["LR"] = pid  # Long reliever prefers high endurance
    if rps:
        pid, _ = rps.pop(0)
        assignment["MR"] = pid  # Middle reliever
    if rps:
        pid, _ = rps.pop(0)
        assignment["SU"] = pid  # Setup
    if rps:
        pid, _ = rps.pop(-1)
        assignment["CL"] = pid  # Closer prefers low endurance

    return assignment
