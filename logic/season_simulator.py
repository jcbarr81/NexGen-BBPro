from __future__ import annotations

from typing import Callable, Dict, Iterable, List
import random

from models.player import Player
from models.pitcher import Pitcher
from logic.simulation import GameSimulation, TeamState
from logic.playbalance_config import PlayBalanceConfig


class SeasonSimulator:
    """Simulate a season schedule with an All-Star break.

    Parameters
    ----------
    schedule:
        Iterable of schedule entries with ``date``, ``home`` and ``away`` keys.
    simulate_game:
        Optional callback accepting ``home`` and ``away`` team identifiers.  If
        not provided a minimal game simulation using :class:`GameSimulation`
        from :mod:`logic.simulation` is performed.
    on_all_star_break:
        Optional callable executed when the season reaches its midpoint.  This
        can be used to run the All-Star exhibition.
    """

    def __init__(
        self,
        schedule: Iterable[Dict[str, str]],
        simulate_game: Callable[[str, str], None] | None = None,
        on_all_star_break: Callable[[], None] | None = None,
        after_game: Callable[[Dict[str, str]], None] | None = None,
    ) -> None:
        self.schedule = list(schedule)
        self.dates: List[str] = sorted({g["date"] for g in self.schedule})
        self._mid = len(self.dates) // 2
        self._index = 0
        self.simulate_game = simulate_game or self._default_simulate_game
        self.on_all_star_break = on_all_star_break
        self._all_star_played = False
        # Callback invoked after each game to persist results such as
        # standings, schedule updates or player statistics.  The callback
        # receives the ``game`` dictionary for the contest that was just
        # simulated.
        self.after_game = after_game

    # ------------------------------------------------------------------
    def remaining_days(self) -> int:
        """Return the number of days left until the All-Star break."""
        return max(self._mid - self._index, 0)

    def simulate_next_day(self) -> None:
        """Simulate games for the next scheduled day.

        When the midpoint of the season is reached the optional
        ``on_all_star_break`` callback is invoked and regular-season play
        automatically resumes immediately afterward.
        """

        if self._index == self._mid and not self._all_star_played:
            if self.on_all_star_break is not None:
                self.on_all_star_break()
            self._all_star_played = True

        if self._index >= len(self.dates):
            return
        current_date = self.dates[self._index]
        games = [g for g in self.schedule if g["date"] == current_date]
        for game in games:
            self.simulate_game(game["home"], game["away"])
            # Allow the caller to persist results after each individual game
            # rather than waiting for the entire day to complete.  This makes
            # it possible to update standings, schedules and statistics even if
            # a simulation run is interrupted mid-day.
            if self.after_game is not None:
                try:
                    self.after_game(game)
                except Exception:  # pragma: no cover - persistence is best effort
                    pass
        self._index += 1

    # ------------------------------------------------------------------
    def _default_simulate_game(self, home_id: str, away_id: str) -> None:
        """Run a minimal game simulation between two placeholder teams.

        The :class:`Player` and :class:`Pitcher` classes require a number of
        positional fields (e.g. ``player_id``, ``birthdate``) which are not
        relevant for a tiny self-contained simulation.  Previously this method
        attempted to instantiate these classes with only names, which raised a
        :class:`TypeError`.  To keep the simulator light-weight while still
        honouring the data model, we construct the objects with simple placeholder
        values for the required attributes.
        """

        def _placeholder(
            cls, first: str, last: str, position: str, **extra
        ):
            """Create a minimal player instance with required attributes."""

            base = dict(
                player_id=f"{first[0]}{last}",
                first_name=first,
                last_name=last,
                birthdate="2000-01-01",
                height=72,
                weight=180,
                bats="R",
                primary_position=position,
                other_positions=[],
                gf=50,
            )
            base.update(extra)
            return cls(**base)

        batter_h = _placeholder(Player, "Home", home_id, "DH")
        pitcher_h = _placeholder(Pitcher, "Home", home_id, "P", fb=50)
        batter_a = _placeholder(Player, "Away", away_id, "DH")
        pitcher_a = _placeholder(Pitcher, "Away", away_id, "P", fb=50)

        home = TeamState(lineup=[batter_h], bench=[], pitchers=[pitcher_h])
        away = TeamState(lineup=[batter_a], bench=[], pitchers=[pitcher_a])

        config = PlayBalanceConfig()
        sim = GameSimulation(home, away, config, random.Random())
        sim.simulate_game()


__all__ = ["SeasonSimulator"]
