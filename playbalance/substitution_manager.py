from __future__ import annotations

"""Utility class handling mid game substitution playbalance.

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
        self._preferred_warm: dict[int, str] = {}

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

        fa_mult = self._cfg_value("defRatFAPct", 100) / 100.0
        arm_mult = self._cfg_value("defRatASPct", 100) / 100.0
        fa = player.fa * fa_mult
        arm = player.arm * arm_mult
        return ((2 * fa * arm) + (fa * fa)) / (arm + 2 * fa + 1)

    def _cfg_value(self, key: str, default: float = 0.0) -> float:
        value = self.config.get(key, default)
        if value is None:
            return default
        return value

    def _pitcher_role(self, pitcher: Pitcher | Player) -> str:
        """Return the assigned pitching role for ``pitcher`` (upper-cased)."""

        role = getattr(pitcher, "assigned_pitching_role", None)
        if role:
            return str(role).upper()
        role = getattr(pitcher, "role", None)
        if role:
            return str(role).upper()
        return ""

    def _reset_pitcher_state(self, state: "PitcherState") -> None:
        """Reset per-appearance fatigue flags for a newly entering pitcher."""

        state.toast = 0.0
        state.is_toast = False
        state.consecutive_hits = 0
        state.consecutive_baserunners = 0
        state.allowed_hr = False
        state.appearance_outs = 0

    def _preferred_warm_pid(self, defense: "TeamState") -> str | None:
        """Return the preferred bullpen pitcher currently warming for ``defense``."""

        return self._preferred_warm.get(id(defense))

    def _set_preferred_warm_pid(self, defense: "TeamState", pid: str | None) -> None:
        """Record or clear the preferred bullpen pitcher for ``defense``."""

        key = id(defense)
        if pid:
            self._preferred_warm[key] = pid
        else:
            self._preferred_warm.pop(key, None)

    def _mark_current_pitcher_exit(self, state: "PitcherState") -> None:
        """Flag ``state`` so the substitution logic will remove the pitcher."""

        if state is None:
            return
        state.is_toast = True
        current_toast = getattr(state, "toast", 0.0) or 0.0
        state.toast = min(current_toast, -999.0)

    def _apply_closer_boost(self, pitcher: Pitcher) -> None:
        """Ensure closers enter with premium late-inning stuff."""

        cfg = self.config
        stuff_floor = int(cfg.get("closerBoostStuffFloor", 92))
        control_floor = int(cfg.get("closerBoostControlFloor", 72))
        control_cap = int(cfg.get("closerBoostControlCap", 85))
        endurance_floor = int(cfg.get("closerBoostEnduranceFloor", 52))

        for attr in ("movement", "fb", "sl", "si"):
            current = getattr(pitcher, attr, None)
            if current is None:
                continue
            if current < stuff_floor:
                setattr(pitcher, attr, stuff_floor)

        control = getattr(pitcher, "control", None)
        if control is not None:
            control = max(control_floor, control)
            control = min(control, control_cap)
            setattr(pitcher, "control", control)

        endurance = getattr(pitcher, "endurance", 0)
        if endurance < endurance_floor:
            setattr(pitcher, "endurance", endurance_floor)

    def _runs_allowed(self, defense: "TeamState", run_diff: int) -> int:
        """Return the number of runs allowed by ``defense`` so far."""

        try:
            total = int(defense.runs + run_diff)
        except Exception:
            total = 0
        return max(0, total)

    def _is_team_no_hitter(self, defense: "TeamState") -> bool:
        """Return True when no hits have been allowed by the current staff."""

        try:
            hits = sum(int(getattr(ps, "h", 0) or 0) for ps in defense.pitcher_stats.values())
        except Exception:
            hits = 0
        return hits == 0

    def _warm_high_leverage(
        self,
        defense: "TeamState",
        *,
        target_role: str,
        inning: int,
        run_diff: int,
        home_team: bool,
    ) -> bool:
        """Schedule a targeted reliever warmup for ``target_role``."""

        cfg = self.config
        exclude: set[str] | None = None
        target = (target_role or "").upper()
        if target == "SU":
            exclude = {
                getattr(p, "player_id", "")
                for p in defense.pitchers
                if self._pitcher_role(p).upper() == "CL"
            }
        idx: int | None
        idx = None
        if len(defense.pitchers) > 1:
            idx, _ = self._select_reliever_index(
                defense,
                inning=inning,
                run_diff=run_diff,
                home_team=home_team,
                exclude=exclude,
            )
        candidate = None
        candidate_role = ""
        if idx is not None and idx < len(defense.pitchers):
            candidate = defense.pitchers[idx]
            candidate_role = self._pitcher_role(candidate).upper() or "MR"
        if candidate is None or candidate_role != target:
            usage = getattr(defense, "usage_status", {}) or {}
            for alt in defense.pitchers[1:]:
                role_token = self._pitcher_role(alt).upper() or "MR"
                if role_token != target:
                    continue
                info = usage.get(getattr(alt, "player_id", ""), {})
                if not info.get("available", True):
                    continue
                candidate = alt
                candidate_role = role_token
                break
        if candidate is None or candidate_role != target:
            return False
        defense.warming_reliever = True
        self._set_preferred_warm_pid(defense, getattr(candidate, "player_id", None))
        tracker = defense.bullpen_warmups.setdefault(candidate.player_id, WarmupTracker(cfg))
        required = self._warmup_required_pitches(candidate, defense)
        setattr(tracker, "required_pitches", required)
        tracker.warm_pitch()
        setattr(
            tracker,
            "warmup_cost",
            min(getattr(tracker, "pitches", 0) or 0, required),
        )
        if target == "CL":
            max_outs = self._max_reliever_outs(target, inning, run_diff)
            max_outs = min(max_outs, 3)
            defense.forced_out_limit_by_pid.setdefault(candidate.player_id, max_outs)
        return True

    def _target_roles(
        self,
        *,
        inning: int,
        run_diff: int,
        starter_left_early: bool = False,
        blowout: bool = False,
    ) -> list[str]:
        """Return preferred bullpen roles for the game context.

        ``run_diff`` is offense.runs - defense.runs. Positive ``run_diff`` means
        defense is trailing. Use simple heuristics to approximate leverage.
        """

        lead = -run_diff
        if starter_left_early:
            return ["LR", "MR", "SU", "CL"]
        if blowout:
            return ["LR", "MR", "SU", "CL"]
        if inning >= 10:
            return ["CL", "SU", "MR", "LR"] if abs(lead) <= 1 else ["MR", "SU", "LR", "CL"]
        if inning <= 5:
            return ["MR", "LR", "SU", "CL"]
        if inning <= 7:
            return ["MR", "SU", "LR", "CL"] if abs(lead) <= 2 else ["MR", "LR", "SU", "CL"]
        if inning == 8:
            return ["SU", "MR", "LR", "CL"] if abs(lead) <= 2 else ["MR", "LR", "SU", "CL"]
        if lead > 0 and lead <= 3:
            return ["CL", "SU", "MR", "LR"]
        if lead == 0:
            return ["SU", "MR", "CL", "LR"]
        return ["MR", "SU", "LR", "CL"]

    def _budget_multiplier(self, role: str) -> float:
        role_key = (role or "").upper()
        if role_key.startswith("SP"):
            role_key = "SP"
        default = float(self.config.get("pitchBudgetMultiplier_MR", 1.8) or 1.8)
        return float(self.config.get(f"pitchBudgetMultiplier_{role_key}", default) or default)

    def _available_budget(
        self,
        pitcher: Pitcher | Player | None,
        role: str,
        usage_info: dict[str, object],
    ) -> tuple[float | None, float | None, float | None]:
        if pitcher is None:
            return None, None, None
        endurance = float(getattr(pitcher, "endurance", 0) or 0)
        if endurance <= 0:
            return None, None, None
        role_key = (role or "").upper()
        if role_key.startswith("SP"):
            soft_limit = float(self.config.get("starterSoftPitchLimitMultiplier", 1.1)) * endurance
            hard_limit = float(self.config.get("starterHardPitchLimitMultiplier", 1.25)) * endurance
            soft_limit = max(soft_limit, float(self.config.get("starterMinSoftPitchLimit", 85)))
            hard_limit = max(hard_limit, float(self.config.get("starterMinHardPitchLimit", 95)))
            max_budget = max(hard_limit, endurance)
        else:
            multiplier = self._budget_multiplier(role_key or "MR")
            max_budget = multiplier * endurance
        pct = usage_info.get("available_pct")
        if pct is None:
            pct = getattr(pitcher, "budget_available_pct", None)
        if pct is None:
            pct_val = 1.0
        else:
            try:
                pct_val = float(pct)
            except (TypeError, ValueError):
                pct_val = 1.0
        pct_val = max(0.0, min(1.0, pct_val))
        available_total = max_budget * pct_val
        return available_total, pct_val, max_budget

    def _warmup_required_pitches(self, pitcher: Pitcher, defense: "TeamState") -> int:
        role = self._pitcher_role(pitcher) or "MR"
        role = role.upper()
        cfg = self.config
        base = float(cfg.get(f"warmupPitchBase_{role}", cfg.get("warmupPitchBase_MR", 12)) or 12)
        exponent = float(cfg.get("warmupAvailabilityExponent", 1.0) or 1.0)
        floor = float(cfg.get("warmupAvailabilityFloor", 0.25) or 0.25)
        usage = getattr(defense, "usage_status", {}) or {}
        info = usage.get(getattr(pitcher, "player_id", ""), {})
        pct = info.get("available_pct")
        if pct is None:
            pct = getattr(pitcher, "budget_available_pct", 1.0)
        try:
            pct = float(pct)
        except (TypeError, ValueError):
            pct = 1.0
        pct = max(0.0, pct)
        pct = max(pct, floor)
        required = int(round(base * (pct ** exponent)))
        override = int(self.config.get("warmupPitchCount", 0) or 0)
        if override > 0:
            required = override
        return max(1, required)

    def _select_reliever_index(
        self,
        defense: "TeamState",
        *,
        inning: int,
        run_diff: int,
        home_team: bool,
        exclude: set[str] | None = None,
    ) -> tuple[int | None, bool]:
        """Return (index, is_emergency) for the preferred, eligible reliever.

        Considers role preferences by inning/leverage and enforces basic
        availability based on ``defense.usage_status`` when present.
        """

        exclude = exclude or set()

        usage = getattr(defense, "usage_status", {}) or {}
        cfg = self.config
        starter_state = defense.current_pitcher_state
        starter_left_early = False
        blowout_margin = int(cfg.get("lrBlowoutMargin", 4) or 4)
        blowout = abs(run_diff) >= blowout_margin
        if starter_state is not None:
            role_token = self._pitcher_role(getattr(starter_state, "player", None))
            if role_token.upper().startswith("SP"):
                outs_recorded = getattr(starter_state, "outs", 0)
                outs_thresh = int(cfg.get("starterEarlyOutsThresh", 12) or 12)
                early_inning_limit = max(4, outs_thresh // 3)
                if outs_recorded < outs_thresh and inning <= early_inning_limit:
                    starter_left_early = True
        roles_pref = self._target_roles(
            inning=inning,
            run_diff=run_diff,
            starter_left_early=starter_left_early,
            blowout=blowout,
        )

        # Build candidate list with metadata
        cand: list[tuple[int, str, dict]] = []
        used = getattr(defense, "used_pitchers", set()) or set()
        for idx, pitcher in enumerate(defense.pitchers):
            if idx == 0:
                continue
            role = self._pitcher_role(pitcher).upper() or "MR"
            if role in {"SP1", "SP2", "SP3", "SP4", "SP5"}:
                continue
            if pitcher.player_id in exclude:
                continue
            if pitcher.player_id in used:
                continue
            info = dict(usage.get(pitcher.player_id, {}))
            info.setdefault("available", True)
            info.setdefault("apps3", 0)
            info.setdefault("apps7", 0)
            info.setdefault("consecutive_days", 0)
            info.setdefault("days_since_use", 9999)
            info.setdefault("last_pitches", 0)
            cand.append((idx, role, info))

        lead = -run_diff
        if lead <= 0:
            non_cl = [item for item in cand if item[1] != "CL"]
            if non_cl:
                cand = non_cl

        # Helper to enforce caps using config
        def _eligible(role: str, info: dict) -> bool:
            cfg = self.config
            # Rest gate
            if not info.get("available", True):
                return False
            consec = int(info.get("consecutive_days", 0) or 0)
            last_p = int(info.get("last_pitches", 0) or 0)
            if role != "SP" and consec >= 2 and int(cfg.get("forbidThirdConsecutiveDay", 1)):
                return False
            if role != "SP" and consec >= 1:
                if last_p > int(cfg.get("b2bMaxPriorPitches", 20)):
                    return False
            # Window caps
            if role != "SP":
                apps3 = int(info.get("apps3", 0) or 0)
                apps7 = int(info.get("apps7", 0) or 0)
                cap3 = int(cfg.get(f"maxApps3Day_{role}", cfg.get("maxApps3Day_MR", 3)))
                cap7 = int(cfg.get(f"maxApps7Day_{role}", cfg.get("maxApps7Day_MR", 5)))
                if apps3 >= cap3 or apps7 >= cap7:
                    return False
            return True

        # Rank candidates by role preference then freshness
        def _score(item: tuple[int, str, dict]) -> tuple[int, float, float]:
            _, role, info = item
            role_rank = roles_pref.index(role) if role in roles_pref else len(roles_pref)
            days_since = float(info.get("days_since_use", 0) or 0.0)
            last_p = float(info.get("last_pitches", 0) or 0.0)
            return (role_rank, -days_since, last_p)

        eligible = [it for it in cand if _eligible(it[1], it[2])]
        if eligible:
            eligible.sort(key=_score)
            return eligible[0][0], False

        return None, False

    def _max_reliever_outs(self, role: str, inning: int, run_diff: int) -> int:
        """Return outing-out limit for the given bullpen ``role``.

        When UsageModelV2 is enabled, use configured caps per role. Otherwise, fall
        back to legacy behavior (CL/SU limited situationally; others effectively unlimited).
        """

        role = (role or "").upper()
        # Starters are never constrained by reliever outing caps
        if role.startswith("SP"):
            return 99
        cfg = self.config
        if int(cfg.get("enableUsageModelV2", 0)):
            if role == "CL":
                return int(cfg.get("maxOuts_CL", 3))
            if role == "SU":
                return int(cfg.get("maxOuts_SU", 4))
            if role == "MR":
                return int(cfg.get("maxOuts_MR", 4))
            if role == "LR":
                return int(cfg.get("maxOuts_LR", 6))
            # Unknown reliever role
            return int(cfg.get("maxOuts_MR", 4))

        leverage_margin = abs(run_diff)
        extras = inning >= 10
        late_leverage = inning >= 9 and leverage_margin <= 1
        if role not in {"CL", "SU"}:
            return 99
        if extras and leverage_margin <= 1:
            return 6
        if late_leverage:
            return 4
        return 3

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
        chance = self._cfg_value("defSubBase", 0)
        if inning <= 6:
            chance += self._cfg_value("defSubBeforeInn7Adjust", 0)
        elif inning == 7:
            chance += self._cfg_value("defSubInn7Adjust", 0)
        elif inning == 8:
            chance += self._cfg_value("defSubInn8Adjust", 0)
        else:
            chance += self._cfg_value("defSubAfterInn8Adjust", 0)

        # Position qualification adjustments
        target_pos = worst.primary_position
        if best.primary_position != target_pos:
            if target_pos in getattr(best, "other_positions", []):
                chance += cfg.get("defSubNoPrimaryPosAdjust", 0)
            else:
                chance += self._cfg_value("defSubNoQualifiedPosAdjust", 0)

        # Injury adjustment on current player
        if getattr(worst, "injured", False):
            chance += self._cfg_value("defSubPerInjuryPointAdjust", 0)

        # Current defender rating adjustments
        curr_def = self._defense_rating(worst)
        if curr_def >= self._cfg_value("defSubVeryHighCurrDefThresh", 0):
            chance += self._cfg_value("defSubVeryHighCurrDefAdjust", 0)
        elif curr_def >= self._cfg_value("defSubHighCurrDefThresh", 0):
            chance += self._cfg_value("defSubHighCurrDefAdjust", 0)
        elif curr_def >= self._cfg_value("defSubMedCurrDefThresh", 0):
            chance += self._cfg_value("defSubMedCurrDefAdjust", 0)
        elif curr_def >= self._cfg_value("defSubLowCurrDefThresh", 0):
            chance += self._cfg_value("defSubLowCurrDefAdjust", 0)
        else:
            chance += self._cfg_value("defSubVeryLowCurrDefAdjust", 0)

        # Potential new defender rating adjustments
        new_def = self._defense_rating(best)
        if new_def >= self._cfg_value("defSubVeryHighNewDefThresh", 0):
            chance += self._cfg_value("defSubVeryHighNewDefAdjust", 0)
        elif new_def >= self._cfg_value("defSubHighNewDefThresh", 0):
            chance += self._cfg_value("defSubHighNewDefAdjust", 0)
        elif new_def >= self._cfg_value("defSubMedNewDefThresh", 0):
            chance += self._cfg_value("defSubMedNewDefAdjust", 0)
        elif new_def >= self._cfg_value("defSubLowNewDefThresh", 0):
            chance += self._cfg_value("defSubLowNewDefAdjust", 0)
        else:
            chance += self._cfg_value("defSubVeryLowNewDefAdjust", 0)

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

        if len(defense.pitchers) <= 1:
            return None
        old_pitcher = defense.pitchers[0]
        bullpen = defense.pitchers[1:]
        used = getattr(defense, "used_pitchers", set()) or set()
        available = [p for p in bullpen if p.player_id not in used]
        if not available:
            available = list(bullpen)
        if not available:
            return None
        new_pitcher = available[0]
        remaining = [p for p in bullpen if p.player_id != new_pitcher.player_id and p.player_id != getattr(old_pitcher, "player_id", None)]
        defense.pitchers = [new_pitcher] + remaining
        state = defense.pitcher_stats.setdefault(
            new_pitcher.player_id, PitcherState(new_pitcher)
        )
        role_new = self._pitcher_role(new_pitcher)
        if str(role_new).upper() == "CL":
            self._apply_closer_boost(new_pitcher)
        self._reset_pitcher_state(state)
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

        usage = getattr(defense, "usage_status", {}) or {}
        player_id = getattr(getattr(state, "player", None), "player_id", "")
        usage_info = usage.get(player_id, {})
        role = ""
        if getattr(state, "player", None) is not None:
            role = self._pitcher_role(state.player)
        role_upper = str(role).upper() if isinstance(role, str) else ""
        available_total, avail_pct_initial, max_budget = self._available_budget(
            state.player, role or "MR", usage_info
        )
        if available_total is None:
            max_budget = self._budget_multiplier(role or "MR") * getattr(state.player, "endurance", 0)
            available_total = max_budget
        remaining = available_total - state.pitches_thrown if available_total is not None else None
        endurance_remaining = float(getattr(state.player, "endurance", 0) - state.pitches_thrown)
        if remaining is None:
            remaining = endurance_remaining
        tired_thresh = cfg.get("pitcherTiredThresh", 0)
        lead = -run_diff
        if remaining is not None:
            remaining = max(0.0, float(remaining))
        budget_pct_remaining = None
        if available_total and available_total > 0:
            budget_pct_remaining = max(0.0, min(1.0, remaining / available_total))
        if getattr(state, "player", None) is not None:
            # Enforce per-role outing caps for relievers only (never for starters)
            if role_upper and not role_upper.startswith("SP"):
                caps_apply = True
                if state.in_save_situation and lead > 0 and role_upper != "CL":
                    caps_apply = False
                if caps_apply:
                    max_outs = self._max_reliever_outs(role, inning, run_diff)
                    if role_upper == "CL":
                        max_outs = min(max_outs, 3)
                    try:
                        forced = defense.forced_out_limit_by_pid.get(state.player.player_id)
                        if forced is not None:
                            max_outs = min(max_outs, int(forced))
                    except Exception:
                        pass
                    if getattr(state, "appearance_outs", 0) >= max_outs:
                        state.is_toast = True
        warmed = False
        role_token = self._pitcher_role(state.player)
        # Proactive warmups for starters cruising late without a shutout/no-hitter.
        proactive_target: str | None = None
        if role_upper.startswith("SP") and inning in (7, 8):
            runs_allowed = self._runs_allowed(defense, run_diff)
            shutout = runs_allowed == 0
            no_hitter = self._is_team_no_hitter(defense)
            lead_cap = int(cfg.get("starterLateWarmLeadMax", 3) or 3)
            if lead >= 0 and lead <= lead_cap and not shutout and not no_hitter:
                if inning == 7:
                    chance = float(cfg.get("starterSeventhWarmChance", 0) or 0.0) / 100.0
                    if chance > 0 and self.rng.random() < chance:
                        proactive_target = "SU"
                else:
                    chance = float(cfg.get("starterEighthWarmChance", 0) or 0.0) / 100.0
                    if chance > 0 and self.rng.random() < chance:
                        proactive_target = "CL"
        if proactive_target:
            warmed_target = False
            preferred_pid = self._preferred_warm_pid(defense)
            preferred_pitcher = None
            if preferred_pid:
                preferred_pitcher = next(
                    (p for p in defense.pitchers if getattr(p, "player_id", None) == preferred_pid),
                    None,
                )
            if (
                preferred_pitcher is not None
                and self._pitcher_role(preferred_pitcher).upper() == proactive_target
            ):
                warmed_target = True
            else:
                warmed_target = self._warm_high_leverage(
                    defense,
                    target_role=proactive_target,
                    inning=inning,
                    run_diff=run_diff,
                    home_team=home_team,
                )
            if warmed_target:
                warmed = True
                defense.warming_reliever = True
                self._mark_current_pitcher_exit(state)
                # Force a preferred identifier when we reused an existing warm pitcher.
                if preferred_pitcher is not None and self._pitcher_role(preferred_pitcher).upper() == proactive_target:
                    self._set_preferred_warm_pid(defense, getattr(preferred_pitcher, "player_id", None))

        if str(role_token).upper().startswith("SP"):
            endurance = getattr(state.player, "endurance", 0)
            soft_limit = float(cfg.get("starterSoftPitchLimitMultiplier", 1.1)) * endurance
            hard_limit = float(cfg.get("starterHardPitchLimitMultiplier", 1.25)) * endurance
            soft_limit = max(soft_limit, float(cfg.get("starterMinSoftPitchLimit", 85)))
            hard_limit = max(hard_limit, float(cfg.get("starterMinHardPitchLimit", 95)))
            soft_limit = min(soft_limit, hard_limit)
            if state.pitches_thrown >= soft_limit:
                defense.warming_reliever = True
                warmed = True
            thresh = self._starter_toast_threshold(defense, inning, home_team)
            toast_trigger = state.toast < thresh or endurance_remaining <= tired_thresh
            # Budget-aware warmup for starters
            budget_trigger = False
            try:
                sp_thresh = float(self.config.get("pitchBudgetAvailThresh_SP", 0.55))
                if budget_pct_remaining is not None and budget_pct_remaining < sp_thresh:
                    budget_trigger = True
            except Exception:
                budget_trigger = False
            if toast_trigger or budget_trigger:
                defense.warming_reliever = True
                warmed = True
        else:
            if budget_pct_remaining is not None:
                pct_left = budget_pct_remaining * 100.0
            else:
                pct_left = (
                    ((remaining or 0.0) / state.player.endurance) * 100
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

        # Proactively prepare the closer for late-inning save situations even when
        # the current reliever is still effective. This keeps setup arms from
        # shouldering ninth-inning duties by default.
        if not defense.warming_reliever and inning >= 8 and 0 < lead <= 3:
            exclude = {player_id} if player_id else set()
            idx, _ = self._select_reliever_index(
                defense,
                inning=inning,
                run_diff=run_diff,
                home_team=home_team,
                exclude=exclude,
            )
            if idx is not None and idx < len(defense.pitchers):
                candidate = defense.pitchers[idx]
                candidate_role = self._pitcher_role(candidate).upper() or "MR"
                wants_closer = candidate_role == "CL"
                wants_setup = candidate_role == "SU" and inning == 8 and lead <= 2
                if (wants_closer and role_upper != "CL") or (wants_setup and role_upper not in {"CL", "SU"}):
                    defense.warming_reliever = True
                    warmed = True
                    required = self._warmup_required_pitches(candidate, defense)
                    tracker = defense.bullpen_warmups.setdefault(
                        candidate.player_id, WarmupTracker(cfg)
                    )
                    setattr(tracker, "required_pitches", required)
                    tracker.warm_pitch()
                    setattr(
                        tracker,
                        "warmup_cost",
                        min(getattr(tracker, "pitches", 0) or 0, required),
                    )
                    # Respect configured outing caps for the high-leverage arm once he enters.
                    max_outs = self._max_reliever_outs(candidate_role, inning, run_diff)
                    max_outs = min(max_outs, 3)
                    defense.forced_out_limit_by_pid.setdefault(
                        candidate.player_id, max_outs
                    )
                    # After preparing the high-leverage arm, flag the current pitcher for removal.
                    self._mark_current_pitcher_exit(state)

        # If warming, record a warmup pitch for the selected reliever
        if defense.warming_reliever and len(defense.pitchers) > 1:
            preferred_pid = self._preferred_warm_pid(defense)
            next_pitcher = None
            if preferred_pid:
                next_pitcher = next(
                    (p for p in defense.pitchers if getattr(p, "player_id", None) == preferred_pid),
                    None,
                )
            if next_pitcher is None:
                idx, _ = self._select_reliever_index(
                    defense,
                    inning=inning,
                    run_diff=run_diff,
                    home_team=home_team,
                )
                if idx is not None:
                    next_pitcher = defense.pitchers[idx]
                    self._set_preferred_warm_pid(defense, getattr(next_pitcher, "player_id", None))
            if next_pitcher is not None:
                tracker = defense.bullpen_warmups.setdefault(
                    next_pitcher.player_id, WarmupTracker(cfg)
                )
                required = self._warmup_required_pitches(next_pitcher, defense)
                setattr(tracker, "required_pitches", required)
                tracker.warm_pitch()
                setattr(
                    tracker,
                    "warmup_cost",
                    min(getattr(tracker, "pitches", 0) or 0, required),
                )

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
        usage = getattr(defense, "usage_status", {}) or {}
        player_id = getattr(getattr(state, "player", None), "player_id", "")
        usage_info = usage.get(player_id, {})
        raw_role = self._pitcher_role(getattr(state, "player", None)) if getattr(state, "player", None) is not None else ""
        role = raw_role or "MR"
        hard_limit_value = None
        available_total, avail_pct_initial, max_budget = self._available_budget(
            state.player, role, usage_info
        )
        if available_total is None:
            max_budget = self._budget_multiplier(role) * getattr(state.player, "endurance", 0)
            available_total = max_budget
        remaining = available_total - state.pitches_thrown if available_total is not None else None
        endurance_remaining = float(getattr(state.player, "endurance", 0) - state.pitches_thrown)
        if remaining is None:
            remaining = endurance_remaining
        if remaining is not None:
            remaining = max(0.0, float(remaining))
        budget_pct_remaining = None
        if available_total and available_total > 0:
            budget_pct_remaining = max(0.0, min(1.0, remaining / available_total))
        exhausted = cfg.get("pitcherExhaustedThresh", 0)
        tired = cfg.get("pitcherTiredThresh", 0)
        lead = -run_diff
        role_token = raw_role
        forced_cap_current = None
        try:
            forced_cap_current = defense.forced_out_limit_by_pid.get(player_id)
        except Exception:
            forced_cap_current = None
        if endurance_remaining <= exhausted:
            defense.warming_reliever = True
        if not defense.warming_reliever:
            # Force a closer handoff in the ninth or later when protecting a small lead.
            if inning >= 9 and 0 < lead <= 3 and str(role_token).upper() != "CL":
                exclude = {player_id} if player_id else set()
                idx, _ = self._select_reliever_index(
                    defense,
                    inning=inning,
                    run_diff=run_diff,
                    home_team=home_team,
                    exclude=exclude,
                )
                if idx is not None and idx < len(defense.pitchers):
                    candidate = defense.pitchers[idx]
                    cand_role = self._pitcher_role(candidate).upper() or "MR"
                    if cand_role == "CL":
                        defense.warming_reliever = True
                        required = self._warmup_required_pitches(candidate, defense)
                        tracker = defense.bullpen_warmups.setdefault(
                            candidate.player_id, WarmupTracker(cfg)
                        )
                        setattr(tracker, "required_pitches", required)
                        tracker.pitches = max(getattr(tracker, "pitches", 0), required)
                        limit = self._max_reliever_outs(cand_role, inning, run_diff)
                        limit = min(limit, 3)
                        defense.forced_out_limit_by_pid.setdefault(
                            candidate.player_id,
                            limit,
                        )
                        state.is_toast = True
            if not defense.warming_reliever:
                return False
        change = False
        if state.in_save_situation and lead > 0 and str(role_token).upper() == "CL":
            defense.warming_reliever = False
            self._set_preferred_warm_pid(defense, None)
            return False
        if str(role_token).upper().startswith("SP"):
            endurance = getattr(state.player, "endurance", 0)
            soft_limit = float(cfg.get("starterSoftPitchLimitMultiplier", 1.1)) * endurance
            hard_limit = float(cfg.get("starterHardPitchLimitMultiplier", 1.25)) * endurance
            soft_limit = max(soft_limit, float(cfg.get("starterMinSoftPitchLimit", 85)))
            hard_limit = max(hard_limit, float(cfg.get("starterMinHardPitchLimit", 95)))
            soft_limit = min(soft_limit, hard_limit)
            hard_limit_value = hard_limit
            thresh = self._starter_toast_threshold(defense, inning, home_team)
            sp_change = False
            if state.pitches_thrown >= hard_limit:
                sp_change = True
            elif state.toast < thresh or endurance_remaining <= tired:
                sp_change = True
            elif thresh <= 0 and state.consecutive_baserunners >= 1:
                sp_change = True
            # Budget-aware replace for starters
            try:
                sp_thresh = float(self.config.get("pitchBudgetAvailThresh_SP", 0.55))
                if budget_pct_remaining is not None and budget_pct_remaining < sp_thresh:
                    sp_change = True
            except Exception:
                pass
            if sp_change:
                change = True
        else:
            if budget_pct_remaining is not None:
                pct_left = budget_pct_remaining * 100.0
            else:
                pct_left = (
                    ((remaining or 0.0) / state.player.endurance) * 100
                    if state.player.endurance
                    else 0
                )
            if (
                state.is_toast
                or pct_left <= cfg.get("pitcherToastPctPitchesLeft", 0)
                or endurance_remaining <= tired
            ):
                change = True
        if not change:
            return False
        # Select reliever by role/availability and ensure he is warm
        idx, emergency = self._select_reliever_index(
            defense,
            inning=inning,
            run_diff=run_diff,
            home_team=home_team,
        )
        next_pitcher = None
        if idx is not None and idx < len(defense.pitchers):
            next_pitcher = defense.pitchers[idx]
        if len(defense.pitchers) > 1 and next_pitcher is not None:
            tracker = defense.bullpen_warmups.get(next_pitcher.player_id)
            required = self._warmup_required_pitches(next_pitcher, defense)
            force_swap = (
                forced_cap_current is not None
                and getattr(defense.current_pitcher_state, "appearance_outs", 0) >= int(forced_cap_current)
            )
            if not force_swap:
                if state.is_toast:
                    force_swap = True
                elif hard_limit_value is not None and state.pitches_thrown >= hard_limit_value:
                    force_swap = True
            if tracker is None or getattr(tracker, "pitches", 0) < required:
                if not force_swap:
                    return False
                tracker = defense.bullpen_warmups.setdefault(next_pitcher.player_id, WarmupTracker(cfg))
                tracker.pitches = required
            setattr(tracker, "required_pitches", required)
            setattr(
                tracker,
                "warmup_cost",
                min(getattr(tracker, "pitches", 0) or 0, required),
            )
        from playbalance.state import PitcherState  # local import to avoid cycle
        if not defense.pitchers:
            return False
        old_pitcher = defense.pitchers[0] if defense.pitchers else None
        new_pitcher = next_pitcher if next_pitcher is not None else (
            defense.pitchers[1] if len(defense.pitchers) > 1 else None
        )
        if new_pitcher is not None:
            # Rebuild list placing selected reliever first, preserving order of unused others
            old_pid = getattr(old_pitcher, "player_id", None)
            remaining = [
                p
                for i, p in enumerate(defense.pitchers)
                if i != 0 and p.player_id != new_pitcher.player_id and p.player_id != old_pid
            ]
            defense.pitchers = [new_pitcher] + remaining
        if new_pitcher is None and run_diff <= -cfg.get("posPlayerPitchingRuns", 0) and defense.bench:
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
            if old_pitcher is not None:
                defense.pitchers.pop(0)
            defense.pitchers.insert(0, new_pitcher)
        if new_pitcher is None:
            defense.warming_reliever = False
            self._set_preferred_warm_pid(defense, None)
            return False
        state = defense.pitcher_stats.setdefault(
            new_pitcher.player_id, PitcherState(new_pitcher)
        )
        role_new = self._pitcher_role(new_pitcher)
        if str(role_new).upper() == "CL":
            self._apply_closer_boost(new_pitcher)
            try:
                limit = self._max_reliever_outs(role_new, inning, run_diff)
            except Exception:
                limit = 3
            limit = min(int(limit), 3)
            defense.forced_out_limit_by_pid[new_pitcher.player_id] = limit
        self._reset_pitcher_state(state)
        defense.current_pitcher_state = state
        defense.warming_reliever = False
        self._set_preferred_warm_pid(defense, None)
        defense.bullpen_warmups.pop(new_pitcher.player_id, None)
        # Emergency handling: force a tighter outs cap and postgame recovery penalty
        if emergency and new_pitcher is not None:
            try:
                cap = int(self.config.get("emergencyOutsCap", 3))
                if cap > 0:
                    defense.forced_out_limit_by_pid[new_pitcher.player_id] = cap
                tax = int(self.config.get("emergencyReliefTaxPitches", 20))
                if tax > 0:
                    prev = defense.postgame_recovery_penalties.get(new_pitcher.player_id, 0)
                    defense.postgame_recovery_penalties[new_pitcher.player_id] = max(prev, tax)
            except Exception:
                pass
        if log is not None:
            log.append(
                f"Pitching change: {new_pitcher.first_name} {new_pitcher.last_name} enters"
            )
        return True

    def maybe_change_pitcher(
        self, defense: "TeamState", log: Optional[list[str]] = None
    ) -> bool:
        warmed = self.maybe_warm_reliever(
            defense, inning=1, run_diff=0, home_team=True
        )
        if len(defense.pitchers) > 1:
            next_pitcher = defense.pitchers[1]
            tracker = defense.bullpen_warmups.setdefault(
                next_pitcher.player_id, WarmupTracker(self.config)
            )
            required = self._warmup_required_pitches(next_pitcher, defense)
            tracker.pitches = max(getattr(tracker, "pitches", 0), required)
            setattr(tracker, "required_pitches", required)
            defense.warming_reliever = True
            self._set_preferred_warm_pid(defense, getattr(next_pitcher, "player_id", None))
        return self.maybe_replace_pitcher(
            defense, inning=1, run_diff=0, home_team=True, log=log
        )


__all__ = ["SubstitutionManager"]
