from __future__ import annotations

"""Utilities for determining playoff qualifiers and bracket scheduling.

This module provides a small :class:`PlayoffManager` that can be used to
select the top teams from regular-season standings, build a simple playoff
bracket and persist that structure for later simulation.  The implementation
is intentionally light‑weight but fully documented and tested so other parts
of the project can rely on a stable API.
"""

from pathlib import Path
from typing import Dict, Iterable, List
import json
import logging
import random

from models.player import Player
from models.pitcher import Pitcher
from logic.playbalance_config import PlayBalanceConfig
from logic.simulation import GameSimulation, TeamState
from logic.season_manager import SeasonManager, SeasonPhase
from utils.path_utils import get_base_dir


class PlayoffManager:
    """Manage playoff qualification and bracket scheduling."""

    def __init__(
        self,
        standings: Dict[str, Dict[str, int]],
        num_qualifiers: int = 4,
        path: str | Path | None = None,
    ) -> None:
        """Create a manager.

        Parameters
        ----------
        standings:
            Mapping of team identifiers to dictionaries containing at least a
            ``wins`` entry and optionally a ``losses`` entry.
        num_qualifiers:
            Number of teams that should qualify for the postseason.
        path:
            Optional destination for persisting the bracket structure.  If not
            provided ``data/playoff_bracket.json`` relative to the project base
            directory is used.
        """

        base_dir = get_base_dir()
        self.standings = standings
        self.num_qualifiers = num_qualifiers
        self.path = (
            Path(path)
            if path is not None
            else base_dir / "data" / "playoff_bracket.json"
        )
        self.bracket: Dict[str, List[List[dict[str, str]]]] = {"rounds": []}

    # ------------------------------------------------------------------
    # Qualifiers and bracket creation
    # ------------------------------------------------------------------
    def determine_qualifiers(self) -> List[str]:
        """Return the top teams based on their win/loss record.

        Teams are sorted by number of wins in descending order.  Ties are
        broken using the fewest losses.  Only the ``num_qualifiers`` teams are
        returned.
        """

        ranked = sorted(
            self.standings.items(),
            key=lambda item: (
                -item[1].get("wins", 0),
                item[1].get("losses", float("inf")),
            ),
        )
        return [team for team, _ in ranked[: self.num_qualifiers]]

    def create_bracket(
        self, teams: Iterable[str]
    ) -> Dict[str, List[List[dict[str, str]]]]:
        """Create a single-elimination bracket from *teams*.

        The ``teams`` iterable should already be ordered from highest to
        lowest seed.  The returned value is a dictionary with a ``rounds`` key
        containing a list for each round.  Each round is itself a list of
        match dictionaries with ``home`` and ``away`` keys.

        Later rounds reference winners by ``winner_<index>`` placeholders where
        ``index`` corresponds to the zero-based game number from preceding
        rounds.  This simple notation allows the bracket to be persisted and
        later resolved by a simulation engine.
        """

        teams = list(teams)
        rounds: List[List[dict[str, str]]] = []
        if len(teams) < 2:
            return {"rounds": rounds}

        # First round pairings: top seed vs bottom seed, etc.
        first_round: List[dict[str, str]] = []
        n = len(teams)
        for i in range(n // 2):
            first_round.append({"home": teams[i], "away": teams[n - 1 - i]})
        rounds.append(first_round)

        # Subsequent rounds reference winners from prior games.
        game_index = 0
        current_round = first_round
        while len(current_round) > 1:
            next_round: List[dict[str, str]] = []
            for i in range(0, len(current_round), 2):
                next_round.append(
                    {
                        "home": f"winner_{game_index + i}",
                        "away": f"winner_{game_index + i + 1}",
                    }
                )
            rounds.append(next_round)
            game_index += len(current_round)
            current_round = next_round

        self.bracket = {"rounds": rounds}
        return self.bracket

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def save_bracket(
        self, bracket: Dict[str, List[List[dict[str, str]]]] | None = None
    ) -> None:
        """Persist *bracket* to disk in JSON format."""

        if bracket is not None:
            self.bracket = bracket
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.bracket, f, indent=2)

    def load_bracket(self) -> Dict[str, List[List[dict[str, str]]]]:
        """Load a previously saved bracket from disk."""

        try:
            with self.path.open("r", encoding="utf-8") as f:
                self.bracket = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.bracket = {"rounds": []}
        return self.bracket

    # ------------------------------------------------------------------
    # Simulation helpers
    # ------------------------------------------------------------------
    def simulate_series(
        self,
        home_id: str,
        away_id: str,
        best_of: int = 7,
        rng: random.Random | None = None,
    ) -> str:
        """Simulate a playoff series and return the winning team.

        A minimal :class:`~logic.simulation.GameSimulation` is executed for each
        game.  The first club to reach the required number of wins advances.

        Parameters
        ----------
        home_id, away_id:
            Identifiers for the two teams in the series.
        best_of:
            Length of the series.  Defaults to a best-of-seven format.
        rng:
            Optional random number generator used for deterministic behaviour
            during testing.
        """

        wins_needed = best_of // 2 + 1
        wins = {home_id: 0, away_id: 0}
        rng = rng or random.Random()
        config = PlayBalanceConfig()

        def _player(prefix: str, team: str) -> Player:
            return Player(
                player_id=f"{prefix}{team}",
                first_name=prefix,
                last_name=team,
                birthdate="2000-01-01",
                height=72,
                weight=180,
                bats="R",
                primary_position="1B",
                other_positions=[],
                gf=50,
            )

        def _pitcher(prefix: str, team: str) -> Pitcher:
            return Pitcher(
                player_id=f"{prefix}{team}P",
                first_name=prefix,
                last_name=team,
                birthdate="2000-01-01",
                height=72,
                weight=180,
                bats="R",
                primary_position="P",
                other_positions=[],
                gf=50,
                fb=50,
                endurance=10000,
            )

        while max(wins.values()) < wins_needed:
            batter_h = _player("Home", home_id)
            batter_a = _player("Away", away_id)
            pitchers_h = [_pitcher("Home", f"{home_id}{i}") for i in range(5)]
            pitchers_a = [_pitcher("Away", f"{away_id}{i}") for i in range(5)]
            home = TeamState(lineup=[batter_h], bench=[], pitchers=pitchers_h)
            away = TeamState(lineup=[batter_a], bench=[], pitchers=pitchers_a)
            sim = GameSimulation(home, away, config, rng)
            sim.simulate_game()
            if home.runs > away.runs:
                wins[home_id] += 1
            else:
                wins[away_id] += 1

        return home_id if wins[home_id] > wins[away_id] else away_id

    def simulate_playoffs(
        self,
        best_of: int = 7,
        rng: random.Random | None = None,
        season_manager: SeasonManager | None = None,
    ) -> str | None:
        """Simulate the entire playoff bracket and return the champion.

        Once the champion is determined the result is logged and the season
        phase is advanced to :data:`SeasonPhase.OFFSEASON`.
        """

        if not self.bracket["rounds"]:
            return None

        rng = rng or random.Random()
        winners: List[str] = []

        for round_games in self.bracket["rounds"]:
            for game in round_games:
                home = game["home"]
                away = game["away"]
                if home.startswith("winner_"):
                    home = winners[int(home.split("_")[1])]
                if away.startswith("winner_"):
                    away = winners[int(away.split("_")[1])]
                winners.append(self.simulate_series(home, away, best_of, rng))

        champion = winners[-1]
        logging.info("Playoff champion: %s", champion)
        manager = season_manager or SeasonManager()
        manager.phase = SeasonPhase.OFFSEASON
        manager.save()
        return champion


__all__ = ["PlayoffManager"]

