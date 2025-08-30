from __future__ import annotations

"""Utilities for moving players between roster levels."""

from models.roster import Roster


def move_player_between_rosters(player_id: str, roster: Roster, source: str, destination: str) -> None:
    """Move *player_id* from *source* to *destination* roster level.

    Parameters
    ----------
    player_id:
        Identifier of the player to move.
    roster:
        Roster object to update.
    source:
        One of ``"act"``, ``"aaa"`` or ``"low"`` indicating the current roster.
    destination:
        One of ``"act"``, ``"aaa"`` or ``"low"`` indicating the target roster.

    Raises
    ------
    ValueError
        If *source* or *destination* is not a valid roster level or the player
        is not present on the source roster.
    """

    valid_levels = {"act", "aaa", "low"}
    if source not in valid_levels or destination not in valid_levels:
        raise ValueError("source and destination must be 'act', 'aaa' or 'low'")
    if source == destination:
        return

    src_list = getattr(roster, source)
    if player_id not in src_list:
        raise ValueError("player not found in source roster")

    dest_list = getattr(roster, destination)
    if player_id in dest_list:
        raise ValueError("player already in destination roster")

    src_list.remove(player_id)
    dest_list.append(player_id)
