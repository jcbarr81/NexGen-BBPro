from __future__ import annotations

"""Utility class handling mid game substitution logic.

The real game features a large amount of logic that decides when teams will
replace players during the game.  For the purposes of the unit tests in this
repository we only model a very small, deterministic subset of that behaviour.

``SubstitutionManager`` centralises these decisions so that the main
``GameSimulation`` class can delegate the various checks to a single place.
Each method operates on the mutable ``TeamState`` structure used by the
simulation and will append a human readable entry to ``log`` whenever a change
occurs.  The log is later displayed in the exhibition game dialog so that the
user can manually verify that substitutions occurred.
"""

import random
from typing import Optional, TYPE_CHECKING

from models.player import Player
from models.pitcher import Pitcher
from .playbalance_config import PlayBalanceConfig

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from .simulation import BatterState, PitcherState, TeamState


class SubstitutionManager:
    """Encapsulate substitution related decisions.

    Only small pieces of the real game's behaviour are implemented – enough
    for the unit tests to exercise the different code paths.  Chances for the
    various substitutions are read from the ``PlayBalance`` configuration.  If
    a required key is missing the chance will simply be zero which results in
    the substitution never triggering.
    """

    def __init__(
        self, config: PlayBalanceConfig, rng: Optional[random.Random] = None
    ) -> None:
        self.config = config
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------
    # Pinch hitting
    # ------------------------------------------------------------------
    def maybe_pinch_hit(
        self, team: "TeamState", idx: int, log: Optional[list[str]] = None
    ) -> Player:
        """Possibly replace ``team.lineup[idx]`` with a bench player.

        The best pinch hitter on the bench replaces the current batter if his
        ``PH`` rating is higher and a random roll succeeds.  The chance is
        controlled by ``doubleSwitchPHAdjust`` to mirror the behaviour that was
        previously implemented directly in ``GameSimulation``.
        """

        if not team.bench:
            return team.lineup[idx]
        chance = self.config.get("doubleSwitchPHAdjust", 0) / 100.0
        starter = team.lineup[idx]
        best = max(team.bench, key=lambda p: p.ph, default=None)
        if (
            best
            and best.ph > starter.ph
            and chance > 0
            and self.rng.random() < chance
        ):
            team.bench.remove(best)
            team.lineup[idx] = best
            if log is not None:
                log.append(
                    f"Pinch hitter {best.first_name} {best.last_name} for {starter.first_name} {starter.last_name}"
                )
            return best
        return starter

    # ------------------------------------------------------------------
    # Pinch running
    # ------------------------------------------------------------------
    def maybe_pinch_run(
        self, team: "TeamState", base: int = 0, log: Optional[list[str]] = None
    ) -> None:
        """Replace the runner on ``base`` with a faster bench player.

        Only base 0 (first base) is considered in the tests.  ``pinchRunChance``
        from the config controls the likelihood of the move.
        """

        chance = self.config.get("pinchRunChance", 0) / 100.0
        runner_state = team.bases[base] if base < len(team.bases) else None
        if not team.bench or runner_state is None or chance <= 0:
            return

        best = max(team.bench, key=lambda p: p.sp, default=None)
        if best and best.sp > runner_state.player.sp and self.rng.random() < chance:
            from .simulation import BatterState  # local import to avoid cycle

            team.bench.remove(best)
            # Replace in batting order
            for i, p in enumerate(team.lineup):
                if p.player_id == runner_state.player.player_id:
                    team.lineup[i] = best
                    break
            state = BatterState(best)
            team.lineup_stats[best.player_id] = state
            team.bases[base] = state
            if log is not None:
                log.append(
                    f"Pinch runner {best.first_name} {best.last_name} for {runner_state.player.first_name} {runner_state.player.last_name}"
                )

    # ------------------------------------------------------------------
    # Defensive substitution
    # ------------------------------------------------------------------
    def maybe_defensive_sub(
        self, team: "TeamState", log: Optional[list[str]] = None
    ) -> None:
        """Swap in a better defensive player from the bench.

        The player in the lineup with the lowest ``GF`` rating is replaced by
        the best bench defender when a random roll – controlled by
        ``defSubChance`` – succeeds.
        """

        chance = self.config.get("defSubChance", 0) / 100.0
        if not team.bench or chance <= 0:
            return
        worst_idx, worst = min(
            enumerate(team.lineup), key=lambda x: x[1].gf, default=(None, None)
        )
        best = max(team.bench, key=lambda p: p.gf, default=None)
        if (
            worst is not None
            and best
            and best.gf > worst.gf
            and self.rng.random() < chance
        ):
            team.bench.remove(best)
            team.bench.append(worst)
            team.lineup[worst_idx] = best
            if log is not None:
                log.append(
                    f"Defensive sub {best.first_name} {best.last_name} for {worst.first_name} {worst.last_name}"
                )

    # ------------------------------------------------------------------
    # Double switch
    # ------------------------------------------------------------------
    def maybe_double_switch(
        self,
        offense: "TeamState",
        defense: "TeamState",
        idx: int,
        log: Optional[list[str]] = None,
    ) -> Optional[Player]:
        """Perform a double switch – pinch hitter and new pitcher.

        When triggered a new pitcher is brought in for the defensive team and a
        pinch hitter replaces the batter at ``idx`` for the offensive team.  The
        likelihood is controlled by ``doubleSwitchChance``.
        """

        chance = self.config.get("doubleSwitchChance", 0) / 100.0
        if (
            chance <= 0
            or not offense.bench
            or len(defense.pitchers) <= 1
        ):
            return None

        if self.rng.random() >= chance:
            return None

        # Change pitcher first
        from .simulation import PitcherState  # local import to avoid cycle

        defense.pitchers.pop(0)
        new_pitcher = defense.pitchers[0]
        state = defense.pitcher_stats.setdefault(
            new_pitcher.player_id, PitcherState(new_pitcher)
        )
        defense.current_pitcher_state = state

        # Pinch hit
        starter = offense.lineup[idx]
        best = max(offense.bench, key=lambda p: p.ph, default=None)
        if best and best.ph > starter.ph:
            offense.bench.remove(best)
            offense.lineup[idx] = best
            if log is not None:
                log.append(
                    f"Double switch: {best.first_name} {best.last_name} for {starter.first_name} {starter.last_name}"
                )
            return best

        return starter

    # ------------------------------------------------------------------
    # Standard pitcher change when tired
    # ------------------------------------------------------------------
    def maybe_change_pitcher(
        self, defense: "TeamState", log: Optional[list[str]] = None
    ) -> bool:
        """Replace the current pitcher when fatigued.

        Returns ``True`` if a change was made, ``False`` otherwise.
        """

        state = defense.current_pitcher_state
        if state is None:
            return False

        remaining = state.player.endurance - state.pitches_thrown
        thresh = self.config.get("pitcherTiredThresh", 0)
        if remaining <= thresh and len(defense.pitchers) > 1:
            from .simulation import PitcherState  # local import to avoid cycle

            defense.pitchers.pop(0)
            new_pitcher = defense.pitchers[0]
            state = defense.pitcher_stats.setdefault(
                new_pitcher.player_id, PitcherState(new_pitcher)
            )
            defense.current_pitcher_state = state
            if log is not None:
                log.append(
                    f"Pitching change: {new_pitcher.first_name} {new_pitcher.last_name} enters"
                )
            return True
        return False


__all__ = ["SubstitutionManager"]

