from __future__ import annotations

from typing import Callable, Dict, Iterable, List
import inspect
import random

from playbalance.game_runner import simulate_game_scores
from utils.pitcher_recovery import PitcherRecoveryTracker


class SeasonSimulator:
    """Simulate a season schedule with an All-Star break."""

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
        self.after_game = after_game
        self._tracker = PitcherRecoveryTracker.instance()

        self._seed_positional = False
        self._seed_keyword = False
        self._seed_required = False
        self._date_param_name: str | None = None
        self._has_var_kwargs = False
        self._analyse_sim_signature()

    # ------------------------------------------------------------------
    def _analyse_sim_signature(self) -> None:
        sig = inspect.signature(self.simulate_game)
        params = sig.parameters
        self._has_var_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        seed_param = params.get("seed")
        if seed_param is not None:
            if seed_param.kind == inspect.Parameter.POSITIONAL_ONLY:
                self._seed_positional = True
            else:
                self._seed_keyword = True
            self._seed_required = seed_param.default is inspect._empty
        elif self._has_var_kwargs:
            self._seed_keyword = True

        if "game_date" in params:
            self._date_param_name = "game_date"
        elif "date" in params:
            self._date_param_name = "date"
        elif self._has_var_kwargs:
            self._date_param_name = "game_date"

    # ------------------------------------------------------------------
    def remaining_days(self) -> int:
        """Return the number of days left until the All-Star break."""

        return max(self._mid - self._index, 0)

    def remaining_schedule_days(self) -> int:
        """Return the number of scheduled days left in the regular season."""

        return max(len(self.dates) - self._index, 0)

    def _call_simulate_game(self, home: str, away: str, seed: int, date_str: str) -> object:
        args: List[object] = [home, away]
        kwargs: Dict[str, object] = {}
        if self._seed_positional:
            args.append(seed)
        elif self._seed_keyword:
            kwargs["seed"] = seed
        elif seed is not None:
            random.seed(seed)
        if self._date_param_name and date_str:
            kwargs[self._date_param_name] = date_str
        return self.simulate_game(*args, **kwargs)

    def simulate_next_day(self) -> None:
        """Simulate games for the next scheduled day."""

        if self._index == self._mid and not self._all_star_played:
            if self.on_all_star_break is not None:
                self.on_all_star_break()
            self._all_star_played = True

        if self._index >= len(self.dates):
            return
        current_date = self.dates[self._index]
        games = [g for g in self.schedule if g["date"] == current_date]
        if not games:
            self._index += 1
            return

        self._tracker.start_day(current_date)
        seeds = [random.randrange(1 << 30) for _ in games]

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

        for game, seed in zip(games, seeds):
            result = self._call_simulate_game(game["home"], game["away"], seed, current_date)
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
        home_id: str,
        away_id: str,
        seed: int | None = None,
        game_date: str | None = None,
    ) -> tuple[int, int, str, dict[str, object]]:
        """Run a full play-balance simulation and return score, HTML and metadata."""

        return simulate_game_scores(home_id, away_id, seed=seed, game_date=game_date)


__all__ = ["SeasonSimulator"]
