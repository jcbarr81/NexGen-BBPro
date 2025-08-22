"""All-Star exhibition game management.

This module provides a small utility for constructing All-Star teams and
simulating a single exhibition game.  It is intentionally lightweight so
that it can be used in tests or simple scripts without any external
dependencies.  Teams are formed by randomly splitting provided player and
pitcher pools and then running :class:`logic.simulation.GameSimulation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple
import random

from models.player import Player
from models.pitcher import Pitcher
from logic.simulation import GameSimulation, TeamState, generate_boxscore


@dataclass
class AllStarTeams:
    """Container for the two All-Star teams."""

    home: TeamState
    away: TeamState


class AllStarManager:
    """Build and simulate a mid-season All-Star exhibition.

    Parameters
    ----------
    players:
        Iterable of position players eligible for the game.
    pitchers:
        Iterable of pitchers eligible for the game.
    rng:
        Optional :class:`random.Random` instance for deterministic
        behaviour during testing.
    """

    def __init__(
        self,
        players: Iterable[Player],
        pitchers: Iterable[Pitcher],
        rng: random.Random | None = None,
    ) -> None:
        self.players: List[Player] = list(players)
        self.pitchers: List[Pitcher] = list(pitchers)
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------
    def _split(self) -> AllStarTeams:
        """Randomly divide the player and pitcher pools into two teams."""

        self.rng.shuffle(self.players)
        self.rng.shuffle(self.pitchers)

        half_players = max(1, len(self.players) // 2)
        half_pitchers = max(1, len(self.pitchers) // 2)

        home = TeamState(
            lineup=self.players[:half_players],
            bench=[],
            pitchers=self.pitchers[:half_pitchers],
        )
        away = TeamState(
            lineup=self.players[half_players:],
            bench=[],
            pitchers=self.pitchers[half_pitchers:],
        )
        return AllStarTeams(home=home, away=away)

    # ------------------------------------------------------------------
    def simulate_exhibition(self) -> dict:
        """Simulate the All-Star game and return a box score dictionary."""

        teams = self._split()
        sim = GameSimulation(teams.home, teams.away, {}, self.rng)
        sim.simulate_game()
        return generate_boxscore(sim.home, sim.away)


__all__ = ["AllStarManager", "AllStarTeams"]
