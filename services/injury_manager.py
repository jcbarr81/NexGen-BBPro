"""Utilities for handling player injuries during simulations.

This module contains helper functions that move players between the active
roster and the disabled list (DL) or injured reserve (IR). When a player is
placed on an injury list a replacement is automatically promoted from the
minors. When that player recovers, the replacement is optionally returned to
AAA to keep roster sizes consistent.
"""

from __future__ import annotations

from models.player import Player
from models.roster import Roster


def place_on_injury_list(player: Player, roster: Roster, list_name: str = "dl") -> None:
    """Move *player* to an injury list and promote a replacement.

    Parameters
    ----------
    player:
        The player who has been injured.
    roster:
        Team roster containing the player.
    list_name:
        Either ``"dl"`` for the disabled list or ``"ir"`` for injured reserve.
    """

    if list_name not in {"dl", "ir"}:
        raise ValueError("list_name must be 'dl' or 'ir'")

    for level in ("act", "aaa", "low"):
        level_list = getattr(roster, level)
        if player.player_id in level_list:
            level_list.remove(player.player_id)
            break

    getattr(roster, list_name).append(player.player_id)
    player.injured = True

    roster.promote_replacements()


def recover_from_injury(player: Player, roster: Roster, destination: str = "act") -> None:
    """Return *player* from an injury list to the roster.

    Parameters
    ----------
    player:
        Player who is ready to return.
    roster:
        Team roster to update.
    destination:
        Roster level to place the player on return. Defaults to the active
        roster.
    """

    for list_name in ("dl", "ir"):
        injury_list = getattr(roster, list_name)
        if player.player_id in injury_list:
            injury_list.remove(player.player_id)
            break

    player.injured = False
    player.injury_description = None
    player.return_date = None

    getattr(roster, destination).append(player.player_id)

    if destination == "act":
        for idx in range(len(roster.act) - 1, -1, -1):
            pid = roster.act[idx]
            if pid != player.player_id:
                roster.aaa.append(roster.act.pop(idx))
                break

