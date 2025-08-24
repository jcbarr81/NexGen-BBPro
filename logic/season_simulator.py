from __future__ import annotations

from typing import Callable, Dict, Iterable, List
import random

from logic.simulation import (
    GameSimulation,
    TeamState,
    generate_boxscore,
    render_boxscore_html,
)
from logic.playbalance_config import PlayBalanceConfig
from utils.lineup_loader import build_default_game_state
from utils.path_utils import get_base_dir


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
            result = self.simulate_game(game["home"], game["away"])
            # If the simulation returned a score tuple, store it on the game so
            # persistence layers can record results and update standings.
            if isinstance(result, tuple):
                if len(result) >= 2:
                    game["result"] = f"{result[0]}-{result[1]}"
                if len(result) >= 3 and isinstance(result[2], str):
                    game["boxscore_html"] = result[2]
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
    def _default_simulate_game(
        self, home_id: str, away_id: str
    ) -> tuple[int, int, str]:
        """Run a full pitch-by-pitch simulation between two teams.

        This constructs team states from the default player and roster data and
        then runs :class:`~logic.simulation.GameSimulation`.  The resulting runs
        scored by each club are returned along with rendered box score HTML so
        callers can persist results or update standings.
        """

        home = build_default_game_state(home_id)
        away = build_default_game_state(away_id)
        cfg = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")
        sim = GameSimulation(home, away, cfg, random.Random())
        sim.simulate_game()
        box = generate_boxscore(home, away)
        html = render_boxscore_html(box, home_name=home_id, away_name=away_id)
        return home.runs, away.runs, html


__all__ = ["SeasonSimulator"]
