"""Logic for handling spring training camp simulations.

The real game would feature complex simulations to evaluate players
before the season begins.  For the purposes of this project the training
camp simply marks each player as ``ready`` which can be used by other
parts of the system to determine if a player is prepared for the regular
season.
"""

from __future__ import annotations

from typing import Iterable

from models.base_player import BasePlayer


def run_training_camp(players: Iterable[BasePlayer]) -> None:
    """Run a spring training simulation and flag players as ready.

    Parameters
    ----------
    players:
        Iterable of player objects participating in camp.
    """

    for player in players:
        player.ready = True

