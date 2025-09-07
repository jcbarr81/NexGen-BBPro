from __future__ import annotations

from typing import Callable, Dict, Iterable, List
import multiprocessing as mp
import random

from logic.simulation import (
    GameSimulation,
    TeamState,
    generate_boxscore,
    render_boxscore_html,
)
from utils.lineup_loader import build_default_game_state
from .sim_config import load_tuned_playbalance_config


def _simulate_game_worker(
    simulate_func: Callable[[str, str], tuple[int, int, str] | tuple[int, int] | None],
    home: str,
    away: str,
    seed: int,
):
    """Wrapper executed in a worker process."""
    try:
        return simulate_func(home, away, seed)
    except TypeError:
        random.seed(seed)
        return simulate_func(home, away)


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

        if len(games) > 1:
            seeds = [random.randrange(1 << 30) for _ in games]

            try:
                with mp.Pool() as pool:
                    results = pool.starmap(
                        _simulate_game_worker,
                        [
                            (self.simulate_game, g["home"], g["away"], s)
                            for g, s in zip(games, seeds)
                        ],
                    )
            except Exception:
                results = [
                    _simulate_game_worker(self.simulate_game, g["home"], g["away"], s)
                    for g, s in zip(games, seeds)
                ]

            for game, result in zip(games, results):
                if isinstance(result, tuple):
                    if len(result) >= 2:
                        game["result"] = f"{result[0]}-{result[1]}"
                    if len(result) >= 3:
                        if isinstance(result[2], str):
                            game["boxscore_html"] = result[2]
                        else:
                            game["extra"] = result[2]
                if self.after_game is not None:
                    try:
                        self.after_game(game)
                    except Exception:  # pragma: no cover - persistence is best effort
                        pass
        else:
            for game in games:
                result = self.simulate_game(game["home"], game["away"])
                if isinstance(result, tuple):
                    if len(result) >= 2:
                        game["result"] = f"{result[0]}-{result[1]}"
                    if len(result) >= 3:
                        if isinstance(result[2], str):
                            game["boxscore_html"] = result[2]
                        else:
                            game["extra"] = result[2]
                if self.after_game is not None:
                    try:
                        self.after_game(game)
                    except Exception:  # pragma: no cover - persistence is best effort
                        pass
        self._index += 1

    # ------------------------------------------------------------------
    @staticmethod
    def _default_simulate_game(
        home_id: str, away_id: str, seed: int | None = None
    ) -> tuple[int, int, str]:
        """Run a full pitch-by-pitch simulation between two teams.

        This constructs team states from the default player and roster data and
        then runs :class:`~logic.simulation.GameSimulation`.  The resulting runs
        scored by each club are returned along with rendered box score HTML so
        callers can persist results or update standings.
        """

        home = build_default_game_state(home_id)
        away = build_default_game_state(away_id)
        cfg, _ = load_tuned_playbalance_config()
        sim = GameSimulation(home, away, cfg, random.Random(seed))
        sim.simulate_game()
        box = generate_boxscore(home, away)
        html = render_boxscore_html(box, home_name=home_id, away_name=away_id)
        return home.runs, away.runs, html


__all__ = ["SeasonSimulator"]
