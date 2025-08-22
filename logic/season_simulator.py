from __future__ import annotations

from typing import Callable, Dict, Iterable, List
import random

from models.player import Player
from models.pitcher import Pitcher
from logic.simulation import GameSimulation, TeamState


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
    ) -> None:
        self.schedule = list(schedule)
        self.dates: List[str] = sorted({g["date"] for g in self.schedule})
        self._mid = len(self.dates) // 2
        self._index = 0
        self.simulate_game = simulate_game or self._default_simulate_game
        self.on_all_star_break = on_all_star_break
        self._all_star_played = False

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
        self._index += 1

    # ------------------------------------------------------------------
    def _default_simulate_game(self, home_id: str, away_id: str) -> None:
        """Run a minimal game simulation between two placeholder teams."""
        batter_h = Player(first_name="Home", last_name=home_id)
        pitcher_h = Pitcher(first_name="Home", last_name=home_id)
        batter_a = Player(first_name="Away", last_name=away_id)
        pitcher_a = Pitcher(first_name="Away", last_name=away_id)
        home = TeamState(lineup=[batter_h], bench=[], pitchers=[pitcher_h])
        away = TeamState(lineup=[batter_a], bench=[], pitchers=[pitcher_a])
        sim = GameSimulation(home, away, {}, random.Random())
        sim.simulate_game()


__all__ = ["SeasonSimulator"]
