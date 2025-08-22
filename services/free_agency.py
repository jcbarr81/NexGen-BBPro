"""Utility helpers for handling free agency.

This module provides simple functions to query which players are
currently unsigned and to sign players to teams.  The functions operate
purely on the in-memory player and team objects which makes them easy to
test and reuse in different contexts.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from models.player import Player
from models.team import Team


def list_unsigned_players(
    players: Dict[str, Player], teams: Iterable[Team]
) -> List[Player]:
    """Return a list of players not assigned to any team's roster.

    Parameters
    ----------
    players:
        Mapping of player ids to :class:`~models.player.Player` objects.
    teams:
        Iterable of :class:`~models.team.Team` instances representing the
        league's teams.
    """

    signed_ids = set()
    for team in teams:
        for roster in (team.act_roster, team.aaa_roster, team.low_roster):
            signed_ids.update(roster)

    return [player for pid, player in players.items() if pid not in signed_ids]


def sign_player_to_team(player_id: str, team: Team, level: str = "act") -> None:
    """Assign *player_id* to *team*'s roster at the specified level.

    Parameters
    ----------
    player_id:
        Identifier of the player to sign.
    team:
        The :class:`~models.team.Team` object representing the destination
        team.
    level:
        Roster level to assign the player to. One of ``"act"`` for the
        active roster, ``"aaa"`` for AAA or ``"low"`` for the low minors.
    """

    rosters = {
        "act": team.act_roster,
        "aaa": team.aaa_roster,
        "low": team.low_roster,
    }
    roster = rosters.get(level)
    if roster is None:
        raise ValueError(f"Unknown roster level: {level}")

    # Prevent duplicates across all rosters
    if any(player_id in r for r in rosters.values()):
        raise ValueError("Player already assigned to a roster")

    roster.append(player_id)

