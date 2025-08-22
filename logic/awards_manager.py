"""Utilities for determining end-of-season awards.

This module provides simple helpers that select award winners based on
season statistics.  The goal is not to perfectly emulate real-world award
voting but to offer a deterministic way to highlight top performers.

Example
-------
>>> manager = AwardsManager(players, batting_stats, pitching_stats)
>>> manager.select_award_winners()
{"MVP": Player(...), "CY_YOUNG": Player(...)}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from models.player import Player


@dataclass
class AwardWinner:
    """Container storing the winning player and their key metric."""

    player: Player
    metric: float


class AwardsManager:
    """Select season awards based on provided statistics.

    Parameters
    ----------
    players:
        Mapping of player identifiers to :class:`~models.player.Player`
        instances.
    batting_stats:
        Statistics keyed by player identifier containing at minimum an
        ``"ops"`` value.
    pitching_stats:
        Statistics keyed by player identifier containing at minimum an
        ``"era"`` value.
    """

    def __init__(
        self,
        players: Mapping[str, Player],
        batting_stats: Mapping[str, Mapping[str, float]],
        pitching_stats: Mapping[str, Mapping[str, float]],
    ) -> None:
        self.players = players
        self.batting_stats = batting_stats
        self.pitching_stats = pitching_stats

    # ------------------------------------------------------------------
    # Award selection helpers
    # ------------------------------------------------------------------
    def select_mvp(self) -> AwardWinner:
        """Return the Most Valuable Player based on OPS."""

        if not self.batting_stats:
            raise ValueError("No batting statistics provided")
        winner_id = max(
            self.batting_stats, key=lambda pid: self.batting_stats[pid].get("ops", 0)
        )
        metric = self.batting_stats[winner_id].get("ops", 0.0)
        return AwardWinner(self.players[winner_id], metric)

    def select_cy_young(self) -> AwardWinner:
        """Return the top pitcher based on ERA."""

        if not self.pitching_stats:
            raise ValueError("No pitching statistics provided")
        winner_id = min(
            self.pitching_stats,
            key=lambda pid: self.pitching_stats[pid].get("era", float("inf")),
        )
        metric = self.pitching_stats[winner_id].get("era", 0.0)
        return AwardWinner(self.players[winner_id], metric)

    def select_award_winners(self) -> Dict[str, AwardWinner]:
        """Return a dictionary of award names mapped to winners."""

        return {
            "MVP": self.select_mvp(),
            "CY_YOUNG": self.select_cy_young(),
        }
