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
from .bullpen import WarmupTracker

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from .simulation import BatterState, TeamState
    from playbalance.state import PitcherState


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
    # Rating helpers
    # ------------------------------------------------------------------
    def _offense_rating(self, player: Player) -> float:
        """Compute the combined Offense rating for ``player``."""

        ch_mult = self.config.get("offRatCHPct", 100) / 100.0
        ph_mult = self.config.get("offRatPHPct", 100) / 100.0
        ch = player.ch * ch_mult
        ph = player.ph * ph_mult
        return ((2 * ch * ph) + (ch * ch)) / (ph + 2 * ch + 1)

    def _slugging_rating(self, player: Player) -> float:
        """Compute the combined Slugging rating for ``player``."""

        ch_mult = self.config.get("slugRatCHPct", 100) / 100.0
        ph_mult = self.config.get("slugRatPHPct", 100) / 100.0
        ch = player.ch * ch_mult
        ph = player.ph * ph_mult
        return ((2 * ph * ch) + (ph * ph)) / (ch + 2 * ph + 1)

    def _defense_rating(self, player: Player) -> float:
        """Compute the combined Defense rating for ``player``."""

        fa_mult = self.config.get("defRatFAPct", 100) / 100.0
        arm_mult = self.config.get("defRatASPct", 100) / 100.0
        fa = player.fa * fa_mult
        arm = player.arm * arm_mult
        return ((2 * fa * arm) + (fa * fa)) / (arm + 2 * fa + 1)

    # ------------------------------------------------------------------
    # Pinch hitting
    # ------------------------------------------------------------------
    def maybe_pinch_hit(
        self, team: "TeamState", idx: int, log: Optional[list[str]] = None
    ) -> Player:
        """Possibly replace ``team.lineup[idx]`` with a bench player.

        The best pinch hitter on the bench replaces the current batter if his
        combined slugging rating is higher and a random roll succeeds.  The chance is
        controlled by ``doubleSwitchPHAdjust`` to mirror the behaviour that was
        previously implemented directly in ``GameSimulation``.
        """

        if not team.bench:
            return team.lineup[idx]
        chance = self.config.get("doubleSwitchPHAdjust", 0) / 100.0
        starter = team.lineup[idx]
        starter_rating = self._slugging_rating(starter)
        best = max(team.bench, key=self._slugging_rating, default=None)
        if (
            best
            and self._slugging_rating(best) > starter_rating
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
    # Pinch hitting for the current pitcher
    # ------------------------------------------------------------------
    def maybe_pinch_hit_for_pitcher(
        self,
        offense: "TeamState",
        defense: "TeamState",
        idx: int,
        *,
        inning: int,
        outs: int,
        log: Optional[list[str]] = None,
    ) -> Player:
        """Possibly pinch hit for ``offense``'s current pitcher.

        Returns the player who will bat at ``idx``.  If a pinch hitter is used
        the next pitcher from the bullpen becomes the new current pitcher.
        """

        if (
            not offense.bench
            or len(offense.pitchers) <= 1
            or offense.current_pitcher_state is None
        ):
            return offense.lineup[idx]

        cfg = self.config
        chance = cfg.get("phForPitcherBase", 0)
        if inning <= 3:
            chance += cfg.get("phForPitcherEarlyInnAdjust", 0)
        elif inning <= 6:
            chance += cfg.get("phForPitcherMiddleInnAdjust", 0)
        else:
            chance += cfg.get("phForPitcherLateInnAdjust", 0)
        if inning == 9:
            chance += cfg.get("phForPitcherInn9Adjust", 0)
        elif inning > 9:
            chance += cfg.get("phForPitcherExtraInnAdjust", 0)
        chance += outs * cfg.get("phForPitcherPerOutAdjust", 0)
        bullpen = max(0, len(offense.pitchers) - 1)
        chance += bullpen * cfg.get("phForPitcherPerBPPitcherAdjust", 0)
        bench = len(offense.bench)
        chance += bench * cfg.get("phForPitcherPerBenchPlayerAdjust", 0)

        run_diff = offense.runs - defense.runs
        if run_diff >= 5:
            chance += cfg.get("phForPitcherBigLeadAdjust", 0)
        elif run_diff >= 1:
            chance += cfg.get("phForPitcherLeadAdjust", 0)
        elif run_diff < 0:
            deficit = -run_diff
            needed = deficit + 1
            count = 0
            for base_idx, loc in ((2, "scoring"), (1, "scoring"), (0, "first")):
                if offense.bases[base_idx] is not None:
                    count += 1
                    if count == needed:
                        if loc == "scoring":
                            chance += cfg.get(
                                "phForPitcherWinRunInScoringPosAdjust", 0
                            )
                        else:
                            chance += cfg.get(
                                "phForPitcherWinRunOnFirstAdjust", 0
                            )
                        break
            else:
                count += 1
                if count == needed:
                    chance += cfg.get("phForPitcherWinRunAtBatAdjust", 0)
                else:
                    count += 1
                    if count == needed:
                        chance += cfg.get("phForPitcherWinRunOnDeckAdjust", 0)
                    else:
                        chance += cfg.get("phForPitcherWinRunInDugoutAdjust", 0)

        state = offense.current_pitcher_state
        remaining = state.player.endurance - state.pitches_thrown
        tired_thresh = cfg.get("pitcherTiredThresh", 0)
        if remaining <= 0:
            chance += cfg.get("phForPitcherExhaustedAdjust", 0)
        elif remaining <= tired_thresh:
            chance += cfg.get("phForPitcherTiredAdjust", 0)
        else:
            chance += cfg.get("phForPitcherRestedAdjust", 0)
        if state.r == 0:
            chance += cfg.get("phForPitcherShutoutAdjust", 0)
        if state.h == 0:
            chance += cfg.get("phForPitcherNoHitterAdjust", 0)
        if getattr(state.player, "injured", False):
            chance += cfg.get("phForPitcherPerInjuryPointAdjust", 0)

        chance = max(0.0, min(100.0, chance))
        if self.rng.random() >= chance / 100.0:
            return offense.lineup[idx]

        starter = offense.lineup[idx]
        best = max(offense.bench, key=self._slugging_rating, default=None)
        if best is None:
            return starter

        offense.bench.remove(best)
        offense.lineup[idx] = best

        from playbalance.state import PitcherState  # local import to avoid cycle

        offense.pitchers.pop(0)
        new_pitcher = offense.pitchers[0]
        state = offense.pitcher_stats.setdefault(
            new_pitcher.player_id, PitcherState(new_pitcher)
        )
        offense.current_pitcher_state = state

        if log is not None:
            log.append(
                "Pinch hitter "
                f"{best.first_name} {best.last_name} for pitcher "
                f"{starter.first_name} {starter.last_name}"
            )
        return best

    # ------------------------------------------------------------------
    # Pinch hitting when a run is required
    # ------------------------------------------------------------------
    def maybe_pinch_hit_need_run(
        self,
        team: "TeamState",
        defense: "TeamState",
        idx: int,
        on_deck_idx: int,
        *,
        inning: int,
        outs: int,
        run_diff: int,
        home_team: bool,
        log: Optional[list[str]] = None,
    ) -> Player:
        """Possibly pinch hit when a run is needed to tie or win.

        Mirrors the ``phForRun*`` configuration table, taking the game context
        and slugging ratings of the players into account.  ``run_diff`` should
        be the offensive team's runs minus the defensive team's runs.
        """

        if not team.bench:
            return team.lineup[idx]

        cfg = self.config
        chance = cfg.get("phForRunBase", 0)

        if inning >= 7:
            chance += cfg.get("phForRunLateInnAdjust", 0)
        if inning == 9:
            chance += cfg.get("phForRunInn9Adjust", 0)
        elif inning > 9:
            chance += cfg.get("phForRunExtraInnAdjust", 0)

        chance += outs * cfg.get("phForRunPerOutAdjust", 0)
        chance += len(team.bench) * cfg.get("phForRunPerBenchPlayerAdjust", 0)
        if getattr(team.lineup[idx], "injured", False):
            chance += cfg.get("phForRunPerInjuryPointAdjust", 0)

        if home_team:
            chance += cfg.get("phForRunHomeAdjust", 0)
        else:
            chance += cfg.get("phForRunAwayAdjust", 0)

        if run_diff >= 5:
            chance += cfg.get("phForRunBigLeadAdjust", 0)
        elif run_diff >= 1:
            chance += cfg.get("phForRunLeadAdjust", 0)
        elif run_diff < 0:
            deficit = -run_diff
            needed = deficit + 1
            count = 0
            for base_idx, loc in ((2, "scoring"), (1, "scoring"), (0, "first")):
                if team.bases[base_idx] is not None:
                    count += 1
                    if count == needed:
                        if loc == "scoring":
                            chance += cfg.get(
                                "phForRunWinRunInScoringPosAdjust", 0
                            )
                        else:
                            chance += cfg.get(
                                "phForRunWinRunOnFirstAdjust", 0
                            )
                        break
            else:
                count += 1
                if count == needed:
                    chance += cfg.get("phForRunWinRunAtBatAdjust", 0)
                else:
                    count += 1
                    if count == needed:
                        chance += cfg.get("phForRunWinRunOnDeckAdjust", 0)
                    else:
                        chance += cfg.get(
                            "phForRunWinRunInDugoutAdjust", 0
                        )

        starter = team.lineup[idx]
        starter_rating = self._slugging_rating(starter)
        on_deck = team.lineup[on_deck_idx]
        on_deck_rating = self._slugging_rating(on_deck)

        best, best_rating = max(
            ((p, self._slugging_rating(p)) for p in team.bench),
            key=lambda pr: pr[1],
            default=(None, 0.0),
        )
        if best is None:
            return starter

        ph_diff = best_rating - starter_rating

        def _apply_rating_adjust(value: float, thresh_suffix: str, adjust_suffix: str) -> int:
            if value >= cfg.get(f"phForRunVeryHigh{thresh_suffix}", 0):
                return cfg.get(f"phForRunVeryHigh{adjust_suffix}", 0)
            if value >= cfg.get(f"phForRunHigh{thresh_suffix}", 0):
                return cfg.get(f"phForRunHigh{adjust_suffix}", 0)
            if value >= cfg.get(f"phForRunMed{thresh_suffix}", 0):
                return cfg.get(f"phForRunMed{adjust_suffix}", 0)
            if value >= cfg.get(f"phForRunLow{thresh_suffix}", 0):
                return cfg.get(f"phForRunLow{adjust_suffix}", 0)
            return cfg.get(f"phForRunVeryLow{adjust_suffix}", 0)

        chance += _apply_rating_adjust(starter_rating, "BatRatThresh", "BatRatAdjust")
        chance += _apply_rating_adjust(on_deck_rating, "ODRatThresh", "ODRatAdjust")
        chance += _apply_rating_adjust(ph_diff, "PHBatDiffRatThresh", "PHBatDiffRatAdjust")

        pitcher = (
            defense.current_pitcher_state.player
            if defense.current_pitcher_state is not None
            else None
        )

        def _has_platoon_advantage(batter: Player) -> bool:
            return pitcher is not None and batter.bats != pitcher.bats

        if _has_platoon_advantage(starter):
            chance += cfg.get("phForRunBatPlatAdvAdjust", 0)
        if _has_platoon_advantage(best):
            chance += cfg.get("phForRunPHPlatAdvAdjust", 0)

        chance = max(0.0, min(100.0, chance))

        if best_rating > starter_rating and self.rng.random() < chance / 100.0:
            team.bench.remove(best)
            team.lineup[idx] = best
            if log is not None:
                log.append(
                    f"Pinch hitter {best.first_name} {best.last_name} for {starter.first_name} {starter.last_name}"
                )
            return best

        return starter

    # ------------------------------------------------------------------
    # Pinch hitting when a hit is required
    # ------------------------------------------------------------------
    def maybe_pinch_hit_need_hit(
        self,
        team: "TeamState",
        idx: int,
        on_deck_idx: int,
        *,
        inning: int,
        outs: int,
        run_diff: int,
        home_team: bool,
        log: Optional[list[str]] = None,
    ) -> Player:
        """Possibly pinch hit when a hit is needed to tie or win.

        The decision is controlled by various ``phForHit*`` configuration
        values.  ``run_diff`` should be the offensive team's runs minus the
        defensive team's runs.
        """

        if not team.bench:
            return team.lineup[idx]

        cfg = self.config
        chance = cfg.get("phForHitBase", 0)

        if inning >= 7:
            chance += cfg.get("phForHitLateInnAdjust", 0)
        if inning == 9:
            chance += cfg.get("phForHitInn9Adjust", 0)
        elif inning > 9:
            chance += cfg.get("phForHitExtraInnAdjust", 0)

        chance += outs * cfg.get("phForHitPerOutAdjust", 0)
        chance += len(team.bench) * cfg.get("phForHitPerBenchPlayerAdjust", 0)

        if home_team:
            chance += cfg.get("phForHitHomeAdjust", 0)
        else:
            chance += cfg.get("phForHitAwayAdjust", 0)

        if run_diff >= 5:
            chance += cfg.get("phForHitBigLeadAdjust", 0)
        elif run_diff >= 1:
            chance += cfg.get("phForHitLeadAdjust", 0)
        elif run_diff < 0:
            deficit = -run_diff
            needed = deficit + 1
            count = 0
            for base_idx, loc in ((2, "scoring"), (1, "scoring"), (0, "first")):
                if team.bases[base_idx] is not None:
                    count += 1
                    if count == needed:
                        if loc == "scoring":
                            chance += cfg.get("phForHitWinRunInScoringPosAdjust", 0)
                        else:
                            chance += cfg.get("phForHitWinRunOnFirstAdjust", 0)
                        break
            else:
                count += 1
                if count == needed:
                    chance += cfg.get("phForHitWinRunAtBatAdjust", 0)
                else:
                    count += 1
                    if count == needed:
                        chance += cfg.get("phForHitWinRunOnDeckAdjust", 0)
                    else:
                        chance += cfg.get("phForHitWinRunInDugoutAdjust", 0)

        starter = team.lineup[idx]
        starter_rating = self._offense_rating(starter)
        on_deck = team.lineup[on_deck_idx]
        on_deck_rating = self._offense_rating(on_deck)

        best, best_rating = max(
            ((p, self._offense_rating(p)) for p in team.bench),
            key=lambda pr: pr[1],
            default=(None, 0.0),
        )
        if best is None:
            return starter

        ph_diff = best_rating - starter_rating

        def _apply_rating_adjust(value: float, thresh_suffix: str, adjust_suffix: str) -> int:
            if value >= cfg.get(f"phForHitVeryHigh{thresh_suffix}", 0):
                return cfg.get(f"phForHitVeryHigh{adjust_suffix}", 0)
            if value >= cfg.get(f"phForHitHigh{thresh_suffix}", 0):
                return cfg.get(f"phForHitHigh{adjust_suffix}", 0)
            if value >= cfg.get(f"phForHitMed{thresh_suffix}", 0):
                return cfg.get(f"phForHitMed{adjust_suffix}", 0)
            if value >= cfg.get(f"phForHitLow{thresh_suffix}", 0):
                return cfg.get(f"phForHitLow{adjust_suffix}", 0)
            return cfg.get(f"phForHitVeryLow{adjust_suffix}", 0)

        chance += _apply_rating_adjust(starter_rating, "BatRatThresh", "BatRatAdjust")
        chance += _apply_rating_adjust(on_deck_rating, "ODRatThresh", "ODRatAdjust")
        chance += _apply_rating_adjust(ph_diff, "PHBatDiffRatThresh", "PHBatDiffRatAdjust")

        chance = max(0.0, min(100.0, chance))

        if best_rating > starter_rating and self.rng.random() < chance / 100.0:
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
        self,
        team: "TeamState",
        base: int = 0,
        *,
        inning: int,
        outs: int,
        run_diff: int,
        log: Optional[list[str]] = None,
    ) -> None:
        """Replace the runner on ``base`` with a faster bench player.

        ``run_diff`` should be the offensive team's runs minus the defensive
        team's runs.
        """

        runner_state = team.bases[base] if base < len(team.bases) else None
        if not team.bench or runner_state is None:
            return

        best = max(team.bench, key=lambda p: p.sp, default=None)
        if best is None or best.sp <= runner_state.player.sp:
            return

        cfg = self.config

        # Base chance depending on occupied base
        if base == 0:
            chance = cfg.get("prChanceOnFirstBase", 0)
        elif base == 1:
            chance = cfg.get("prChanceOnSecondBase", 0)
        else:
            chance = cfg.get("prChanceOnThirdBase", 0)

        # Run situation adjustments
        if run_diff == 0:
            chance += cfg.get("prChanceWinningRun", 0)
        elif run_diff == -1:
            chance += cfg.get("prChanceTyingRun", 0)
        else:
            chance += cfg.get("prChanceInsignificant", 0)

        # Outs and inning adjustments
        chance += outs * cfg.get("prChancePerOutAdjust", 0)
        if inning <= 3:
            chance += cfg.get("prChanceEarlyInnAdjust", 0)
        elif inning <= 6:
            chance += cfg.get("prChanceMidInnAdjust", 0)
        else:
            chance += cfg.get("prChanceLateInnAdjust", 0)
        if inning == 9:
            chance += cfg.get("prChanceInn9Adjust", 0)
        elif inning > 9:
            chance += cfg.get("prChanceExtraInnAdjust", 0)

        # Bench and injury adjustments
        chance += len(team.bench) * cfg.get("prChancePerBenchPlayerAdjust", 0)
        if getattr(runner_state.player, "injured", False):
            chance += cfg.get("prChancePerInjuryPointAdjust", 0)

        # Current runner speed adjustments
        sp = runner_state.player.sp
        if sp >= cfg.get("prChanceVeryFastSPThresh", 0):
            chance += cfg.get("prChanceVeryFastSPAdjust", 0)
        elif sp >= cfg.get("prChanceFastSPThresh", 0):
            chance += cfg.get("prChanceFastSPAdjust", 0)
        elif sp >= cfg.get("prChanceMedSPThresh", 0):
            chance += cfg.get("prChanceMedSPAdjust", 0)
        elif sp >= cfg.get("prChanceSlowSPThresh", 0):
            chance += cfg.get("prChanceSlowSPAdjust", 0)
        else:
            chance += cfg.get("prChanceVerySlowSPAdjust", 0)

        # Candidate pinch runner speed adjustments
        pr_sp = best.sp
        if pr_sp >= cfg.get("prChanceVeryFastPRThresh", 0):
            chance += cfg.get("prChanceVeryFastPRAdjust", 0)
        elif pr_sp >= cfg.get("prChanceFastPRThresh", 0):
            chance += cfg.get("prChanceFastPRAdjust", 0)
        elif pr_sp >= cfg.get("prChanceMedPRThresh", 0):
            chance += cfg.get("prChanceMedPRAdjust", 0)
        elif pr_sp >= cfg.get("prChanceSlowPRThresh", 0):
            chance += cfg.get("prChanceSlowPRAdjust", 0)
        else:
            chance += cfg.get("prChanceVerySlowPRAdjust", 0)

        chance = max(0.0, min(100.0, chance))
        if self.rng.random() >= chance / 100.0:
            return

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
        self, team: "TeamState", inning: int, log: Optional[list[str]] = None
    ) -> None:
        """Swap in a better defensive player from the bench.

        ``defSubBase`` provides the base chance for a defensive substitution.
        This value is then modified by a number of situational adjustments such
        as inning, position qualification and the defensive ratings of the
        current and potential players.  The final chance is clamped to ``0-100``
        and interpreted as a percentage.
        """

        if not team.bench:
            return

        worst_idx, worst = min(
            enumerate(team.lineup),
            key=lambda x: self._defense_rating(x[1]),
            default=(None, None),
        )
        best = max(team.bench, key=self._defense_rating, default=None)
        if (
            worst is None
            or best is None
            or self._defense_rating(best) <= self._defense_rating(worst)
        ):
            return

        cfg = self.config

        # Base chance and inning adjustments
        chance = cfg.get("defSubBase", 0)
        if inning <= 6:
            chance += cfg.get("defSubBeforeInn7Adjust", 0)
        elif inning == 7:
            chance += cfg.get("defSubInn7Adjust", 0)
        elif inning == 8:
            chance += cfg.get("defSubInn8Adjust", 0)
        else:
            chance += cfg.get("defSubAfterInn8Adjust", 0)

        # Position qualification adjustments
        target_pos = worst.primary_position
        if best.primary_position != target_pos:
            if target_pos in getattr(best, "other_positions", []):
                chance += cfg.get("defSubNoPrimaryPosAdjust", 0)
            else:
                chance += cfg.get("defSubNoQualifiedPosAdjust", 0)

        # Injury adjustment on current player
        if getattr(worst, "injured", False):
            chance += cfg.get("defSubPerInjuryPointAdjust", 0)

        # Current defender rating adjustments
        curr_def = self._defense_rating(worst)
        if curr_def >= cfg.get("defSubVeryHighCurrDefThresh", 0):
            chance += cfg.get("defSubVeryHighCurrDefAdjust", 0)
        elif curr_def >= cfg.get("defSubHighCurrDefThresh", 0):
            chance += cfg.get("defSubHighCurrDefAdjust", 0)
        elif curr_def >= cfg.get("defSubMedCurrDefThresh", 0):
            chance += cfg.get("defSubMedCurrDefAdjust", 0)
        elif curr_def >= cfg.get("defSubLowCurrDefThresh", 0):
            chance += cfg.get("defSubLowCurrDefAdjust", 0)
        else:
            chance += cfg.get("defSubVeryLowCurrDefAdjust", 0)

        # Potential new defender rating adjustments
        new_def = self._defense_rating(best)
        if new_def >= cfg.get("defSubVeryHighNewDefThresh", 0):
            chance += cfg.get("defSubVeryHighNewDefAdjust", 0)
        elif new_def >= cfg.get("defSubHighNewDefThresh", 0):
            chance += cfg.get("defSubHighNewDefAdjust", 0)
        elif new_def >= cfg.get("defSubMedNewDefThresh", 0):
            chance += cfg.get("defSubMedNewDefAdjust", 0)
        elif new_def >= cfg.get("defSubLowNewDefThresh", 0):
            chance += cfg.get("defSubLowNewDefAdjust", 0)
        else:
            chance += cfg.get("defSubVeryLowNewDefAdjust", 0)

        chance = max(0.0, min(100.0, chance))
        if self.rng.random() >= chance / 100.0:
            return

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

        A number of heuristics based on ``PB.INI`` parameters influence the
        likelihood of the move.  ``doubleSwitchBase`` provides the base chance
        which is then modified by a variety of adjustments such as whether the
        current pitcher is due to bat or how well the involved players defend.
        The final value is clamped to ``0-100`` and interpreted as a percentage
        chance.  ``None`` is returned if the double switch is not attempted.
        """

        if not offense.bench or len(defense.pitchers) <= 1:
            return None

        starter = offense.lineup[idx]
        starter_rating = self._slugging_rating(starter)
        best = max(offense.bench, key=self._slugging_rating, default=None)
        if not best or self._slugging_rating(best) <= starter_rating:
            return None

        # Base chance and simple adjustments
        chance_pct = self.config.get("doubleSwitchBase", 0)

        # Pitcher due to bat next half inning?
        if defense.batting_index == len(defense.lineup):
            chance_pct += self.config.get("doubleSwitchPitcherDueAdjust", 0)

        # Pinch hitter is being used
        chance_pct += self.config.get("doubleSwitchPHAdjust", 0)

        # Position related adjustments
        target_pos = starter.primary_position
        if best.primary_position != target_pos:
            chance_pct += self.config.get("doubleSwitchNoPrimaryPosAdjust", 0)
        if target_pos not in [best.primary_position] + getattr(best, "other_positions", []):
            chance_pct += self.config.get("doubleSwitchNoQualifiedPosAdjust", 0)

        # Defensive rating thresholds for the current player
        curr_def = self._defense_rating(starter)
        if curr_def > self.config.get("doubleSwitchVeryHighCurrDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchVeryHighCurrDefAdjust", 0)
        elif curr_def > self.config.get("doubleSwitchHighCurrDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchHighCurrDefAdjust", 0)
        elif curr_def > self.config.get("doubleSwitchMedCurrDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchMedCurrDefAdjust", 0)
        elif curr_def > self.config.get("doubleSwitchLowCurrDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchLowCurrDefAdjust", 0)
        else:
            chance_pct += self.config.get("doubleSwitchVeryLowCurrDefAdjust", 0)

        # Defensive rating thresholds for the potential substitute
        new_def = self._defense_rating(best)
        if new_def > self.config.get("doubleSwitchVeryHighNewDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchVeryHighNewDefAdjust", 0)
        elif new_def > self.config.get("doubleSwitchHighNewDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchHighNewDefAdjust", 0)
        elif new_def > self.config.get("doubleSwitchMedNewDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchMedNewDefAdjust", 0)
        elif new_def > self.config.get("doubleSwitchLowNewDefThresh", 0):
            chance_pct += self.config.get("doubleSwitchLowNewDefAdjust", 0)
        else:
            chance_pct += self.config.get("doubleSwitchVeryLowNewDefAdjust", 0)

        chance_pct = max(0, min(100, chance_pct))
        if self.rng.random() >= chance_pct / 100.0:
            return None

        # Change pitcher first
        from playbalance.state import PitcherState  # local import to avoid cycle

        defense.pitchers.pop(0)
        new_pitcher = defense.pitchers[0]
        state = defense.pitcher_stats.setdefault(
            new_pitcher.player_id, PitcherState(new_pitcher)
        )
        defense.current_pitcher_state = state

        # Pinch hit
        offense.bench.remove(best)
        offense.lineup[idx] = best
        if log is not None:
            log.append(
                f"Double switch: {best.first_name} {best.last_name} for {starter.first_name} {starter.last_name}"
            )
        return best

    # ------------------------------------------------------------------
    # Pitcher toast helpers
    # ``state.toast`` tracks numeric toast points. ``state.is_toast`` is a
    # boolean flag set when a pitcher has been deemed toast and should be
    # considered for replacement.
    # ------------------------------------------------------------------
    def _starter_toast_threshold(
        self, team: "TeamState", inning: int, home_team: bool
    ) -> int:
        cfg = self.config
        if inning <= 9:
            base = cfg.get(f"starterToastThreshInn{inning}", 0)
        else:
            base = cfg.get("starterToastThreshInn9", 0) + (
                inning - 9
            ) * cfg.get("starterToastThreshPerInn", 0)
        if not home_team:
            base += cfg.get("starterToastThreshAwayAdjust", 0)
        bullpen_pitches = sum(p.endurance for p in team.pitchers[1:])
        innings_left = max(1, min(8, 9 - inning))
        per_inn = bullpen_pitches / innings_left if innings_left > 0 else bullpen_pitches
        if per_inn < 50:
            base += cfg.get("starterToastThreshFewBullpenPitchesAdjust", 0)
        elif per_inn > 100:
            base += cfg.get("starterToastThreshManyBullpenPitchesAdjust", 0)
        return base

    def maybe_warm_reliever(
        self,
        defense: "TeamState",
        *,
        inning: int,
        run_diff: int,
        home_team: bool,
    ) -> bool:
        state = defense.current_pitcher_state
        if state is None or len(defense.pitchers) <= 1:
            return False
        cfg = self.config
        # Progress cooldown for any bullpen pitchers
        step = cfg.get("warmupSecsPerWarmPitch", 0)
        for tracker in defense.bullpen_warmups.values():
            tracker.advance(step)

        remaining = state.player.endurance - state.pitches_thrown
        tired_thresh = cfg.get("pitcherTiredThresh", 0)
        warmed = False
        if state.player.role == "SP":
            thresh = self._starter_toast_threshold(defense, inning, home_team)
            if state.toast < thresh or remaining <= tired_thresh:
                defense.warming_reliever = True
                warmed = True
        else:
            pct_left = (
                (remaining / state.player.endurance) * 100
                if state.player.endurance
                else 0
            )
            max_lead = cfg.get("pitcherToastMaxLead", 0)
            min_lead = cfg.get("pitcherToastMinLead", 0)
            if state.consecutive_baserunners >= 2:
                state.is_toast = True
            if state.allowed_hr and min_lead <= run_diff <= max_lead:
                state.is_toast = True
            state.allowed_hr = False
            if (
                state.is_toast
                or pct_left <= cfg.get("pitcherToastPctPitchesLeft", 0)
                or remaining <= tired_thresh
            ):
                defense.warming_reliever = True
                warmed = True

        # If warming, record a warmup pitch for the next reliever
        if defense.warming_reliever and len(defense.pitchers) > 1:
            next_pitcher = defense.pitchers[1]
            tracker = defense.bullpen_warmups.setdefault(
                next_pitcher.player_id, WarmupTracker(cfg)
            )
            tracker.warm_pitch()

        return warmed

    def maybe_replace_pitcher(
        self,
        defense: "TeamState",
        *,
        inning: int,
        run_diff: int,
        home_team: bool,
        log: Optional[list[str]] = None,
    ) -> bool:
        state = defense.current_pitcher_state
        if state is None:
            return False
        cfg = self.config
        remaining = state.player.endurance - state.pitches_thrown
        exhausted = cfg.get("pitcherExhaustedThresh", 0)
        tired = cfg.get("pitcherTiredThresh", 0)
        if remaining <= exhausted:
            defense.warming_reliever = True
        if not defense.warming_reliever:
            return False
        change = False
        if state.player.role == "SP":
            thresh = self._starter_toast_threshold(defense, inning, home_team)
            if state.toast < thresh or remaining <= tired:
                change = True
        else:
            pct_left = (
                (remaining / state.player.endurance) * 100
                if state.player.endurance
                else 0
            )
            if (
                state.is_toast
                or pct_left <= cfg.get("pitcherToastPctPitchesLeft", 0)
                or remaining <= tired
            ):
                change = True
        if not change:
            return False
        # Ensure next reliever has completed warmup
        if len(defense.pitchers) > 1:
            req = cfg.get("warmupPitchCount", 0)
            if req > 0:
                next_pitcher = defense.pitchers[1]
                tracker = defense.bullpen_warmups.get(next_pitcher.player_id)
                if tracker is None or not tracker.is_ready():
                    return False
        from playbalance.state import PitcherState  # local import to avoid cycle
        if not defense.pitchers:
            return False
        defense.pitchers.pop(0)
        if defense.pitchers:
            new_pitcher = defense.pitchers[0]
        elif run_diff <= -cfg.get("posPlayerPitchingRuns", 0) and defense.bench:
            from models.pitcher import Pitcher

            player = defense.bench.pop(0)
            new_pitcher = Pitcher(
                player_id=player.player_id,
                first_name=player.first_name,
                last_name=player.last_name,
                birthdate=player.birthdate,
                height=player.height,
                weight=player.weight,
                bats=player.bats,
                primary_position=player.primary_position,
                other_positions=player.other_positions,
                gf=player.gf,
                endurance=0,
                control=50,
                movement=50,
                hold_runner=50,
                fb=50,
                cu=0,
                cb=0,
                sl=0,
                si=0,
                scb=0,
                kn=0,
                arm=player.arm,
                fa=player.fa,
                role="RP",
            )
            defense.pitchers.insert(0, new_pitcher)
        else:
            defense.warming_reliever = False
            return False
        state = defense.pitcher_stats.setdefault(
            new_pitcher.player_id, PitcherState(new_pitcher)
        )
        defense.current_pitcher_state = state
        defense.warming_reliever = False
        defense.bullpen_warmups.pop(new_pitcher.player_id, None)
        if log is not None:
            log.append(
                f"Pitching change: {new_pitcher.first_name} {new_pitcher.last_name} enters"
            )
        return True

    def maybe_change_pitcher(
        self, defense: "TeamState", log: Optional[list[str]] = None
    ) -> bool:
        self.maybe_warm_reliever(
            defense, inning=1, run_diff=0, home_team=True
        )
        return self.maybe_replace_pitcher(
            defense, inning=1, run_diff=0, home_team=True, log=log
        )


__all__ = ["SubstitutionManager"]

