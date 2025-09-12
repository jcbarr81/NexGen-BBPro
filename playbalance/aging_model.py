from __future__ import annotations

from typing import Dict, List

from models.base_player import BasePlayer
from playbalance.aging import age_player, calculate_age

RETIREMENT_AGE = 40


def age_and_retire(players: Dict[str, BasePlayer]) -> List[BasePlayer]:
    """Age ``players`` and remove those meeting retirement criteria.

    Parameters
    ----------
    players:
        Mapping of player ids to :class:`~models.base_player.BasePlayer` objects.
        Players are aged in place and any who meet the retirement threshold are
        removed from the mapping and returned.
    """

    retired: List[BasePlayer] = []
    for pid, player in list(players.items()):
        age_player(player)
        if calculate_age(player.birthdate) >= RETIREMENT_AGE:
            retired.append(players.pop(pid))
    return retired
