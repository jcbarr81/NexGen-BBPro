from __future__ import annotations

from typing import Callable, Dict, Iterable, List
import multiprocessing as mp
import random

from playbalance.game_runner import simulate_game_scores




def _simulate_game_worker(
    simulate_func: Callable[[str, str], tuple[int, int] | tuple[int, int, str] | tuple[int, int, str, dict[str, object]] | None],
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
        from :mod:`playbalance.simulation` is performed.
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

        def _apply_result_to_game(game: Dict[str, str], result) -> None:
            if not isinstance(result, tuple):
                return
            if len(result) >= 2:
                game["result"] = f"{result[0]}-{result[1]}"
            meta_index = 2
            if len(result) > 2:
                third = result[2]
                if isinstance(third, str):
                    game["boxscore_html"] = third
                else:
                    game["extra"] = third
                meta_index = 3
            if len(result) > meta_index:
                game["extra"] = result[meta_index]

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
                _apply_result_to_game(game, result)
                if self.after_game is not None:
                    try:
                        self.after_game(game)
                    except Exception:  # pragma: no cover - persistence is best effort
                        pass
        else:
            for game in games:
                result = self.simulate_game(game["home"], game["away"])
                _apply_result_to_game(game, result)
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
    ) -> tuple[int, int, str, dict[str, object]]:
        """Run a full play-balance simulation and return score, HTML and metadata."""

        return simulate_game_scores(home_id, away_id, seed=seed)


__all__ = ["SeasonSimulator"]
