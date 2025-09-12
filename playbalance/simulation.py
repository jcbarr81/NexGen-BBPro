from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, fields, replace
from typing import Dict, List, Optional, Tuple

from models.player import Player
from models.pitcher import Pitcher
from models.team import Team
from playbalance.defensive_manager import DefensiveManager
from playbalance.offensive_manager import OffensiveManager
from playbalance.substitution_manager import SubstitutionManager
from playbalance.playbalance_config import PlayBalanceConfig
from playbalance.physics import Physics, bat_impact as bat_impact_func
from playbalance.pitcher_ai import PitcherAI
from playbalance.batter_ai import BatterAI
from playbalance.bullpen import WarmupTracker
from playbalance.fielding_ai import FieldingAI
from playbalance.field_geometry import DEFAULT_POSITIONS, Stadium
from playbalance.state import PitcherState
from utils.path_utils import get_base_dir
from utils.putout_probabilities import load_putout_probabilities
from utils.stats_persistence import save_stats
from .stats import (
    compute_batting_derived,
    compute_batting_rates,
    compute_pitching_derived,
    compute_pitching_rates,
    compute_fielding_derived,
    compute_fielding_rates,
    compute_team_derived,
    compute_team_rates,
)

from .constants import PITCH_RATINGS


@dataclass(slots=True)
class BatterState:
    """Tracks state and statistics for a batter during the game."""

    player: Player
    pa: int = 0  # Plate appearances
    ab: int = 0  # At bats
    r: int = 0  # Runs scored
    h: int = 0  # Hits
    b1: int = 0  # Singles
    b2: int = 0  # Doubles
    b3: int = 0  # Triples
    hr: int = 0  # Home runs
    rbi: int = 0  # Runs batted in
    bb: int = 0  # Walks
    ibb: int = 0  # Intentional walks
    hbp: int = 0  # Hit by pitch
    so: int = 0  # Strikeouts
    so_looking: int = 0  # Called third strikes
    so_swinging: int = 0  # Swinging strikeouts
    sh: int = 0  # Sacrifice hits
    sf: int = 0  # Sacrifice flies
    roe: int = 0  # Reached on error
    fc: int = 0  # Fielder's choice
    ci: int = 0  # Catcher's interference
    gidp: int = 0  # Ground into double play
    sb: int = 0  # Stolen bases
    cs: int = 0  # Caught stealing
    po: int = 0  # Pickoffs
    pocs: int = 0  # Pickoff caught stealing
    pitches: int = 0  # Pitches seen
    lob: int = 0  # Left on base
    lead: int = 0  # Lead level
    gb: int = 0  # Ground balls put in play
    ld: int = 0  # Line drives put in play
    fb: int = 0  # Fly balls put in play



@dataclass(slots=True)
class FieldingState:
    """Tracks defensive statistics for a player."""

    player: Player
    g: int = 0  # Games fielded
    gs: int = 0  # Games started
    po: int = 0  # Putouts
    a: int = 0  # Assists
    e: int = 0  # Errors
    dp: int = 0  # Double plays
    tp: int = 0  # Triple plays
    pk: int = 0  # Pickoffs
    pb: int = 0  # Passed balls
    ci: int = 0  # Catcher's interference
    cs: int = 0  # Runners caught stealing
    sba: int = 0  # Stolen base attempts against


@dataclass(slots=True)
class TeamState:
    """Mutable state for a team during a game."""

    lineup: List[Player]
    bench: List[Player]
    pitchers: List[Pitcher]
    team: Team | None = None
    lineup_stats: Dict[str, BatterState] = field(default_factory=dict)
    pitcher_stats: Dict[str, PitcherState] = field(default_factory=dict)
    fielding_stats: Dict[str, FieldingState] = field(default_factory=dict)
    batting_index: int = 0
    bases: List[Optional[BatterState]] = field(default_factory=lambda: [None, None, None])
    base_pitchers: List[Optional[PitcherState]] = field(
        default_factory=lambda: [None, None, None]
    )
    runs: int = 0
    inning_runs: List[int] = field(default_factory=list)
    lob: int = 0
    inning_lob: List[int] = field(default_factory=list)
    inning_events: List[List[str]] = field(default_factory=list)
    team_stats: Dict[str, float] = field(default_factory=dict)
    warming_reliever: bool = False
    bullpen_warmups: Dict[str, WarmupTracker] = field(default_factory=dict)
    current_pitcher_state: PitcherState | None = None

    def __post_init__(self) -> None:
        if self.pitchers:
            starter = self.pitchers[0]
            state = PitcherState()
            state.player = starter
            self.pitcher_stats[starter.player_id] = state
            self.current_pitcher_state = state
            state.g = getattr(state, "g", 0) + 1
            state.gs = getattr(state, "gs", 0) + 1
            fs = self.fielding_stats.setdefault(starter.player_id, FieldingState(starter))
            fs.g += 1
            fs.gs += 1
        else:
            self.current_pitcher_state = None
        for p in self.lineup:
            fs = self.fielding_stats.setdefault(p.player_id, FieldingState(p))
            fs.g += 1
            fs.gs += 1

    def __getstate__(self):
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    def __setstate__(self, state):
        for name, value in state.items():
            setattr(self, name, value)


class GameSimulation:
    """A very small game simulation used for tests.

    The goal of this module is not to be feature complete, but to provide
    a minimal game loop that can reason about innings, at-bats and simple
    strategies such as pinch hitting, stealing and pitching changes.  The
    behaviour is heavily driven by values from the parsed PB.INI file so
    that tests can verify that configuration is respected.
    """

    def __init__(
        self,
        home: TeamState,
        away: TeamState,
        config: PlayBalanceConfig,
        rng: Optional[random.Random] = None,
        *,
        surface: str = "grass",
        wet: bool = False,
        temperature: float = 70.0,
        altitude: float = 0.0,
        wind_speed: float = 0.0,
        stadium: Stadium | None = None,
    ) -> None:
        self.home = home
        self.away = away
        self.config = config
        self.rng = rng or random.Random()
        self.defense = DefensiveManager(config, self.rng)
        self.offense = OffensiveManager(config, self.rng)
        self.subs = SubstitutionManager(config, self.rng)
        self.physics = Physics(config, self.rng)
        self.pitcher_ai = PitcherAI(config, self.rng)
        self.batter_ai = BatterAI(config)
        self.fielding_ai = FieldingAI(config, self.rng)
        self.debug_log: List[str] = []
        self.pitches_since_pickoff = 4
        self.current_outs = 0
        self.infield_fly: bool = False
        self.current_field_positions: Dict[
            str, Dict[str, Dict[str, Tuple[float, float]]]
        ] = {}
        self.current_infield_situation = "normal"
        self.current_outfield_situation = "normal"
        self.surface = surface
        self.wet = wet
        self.temperature = temperature
        self.altitude = altitude
        self.wind_speed = wind_speed
        self.stadium = stadium or Stadium()
        self.last_batted_ball_angles: tuple[float, float] | None = None
        self.last_batted_ball_type: str | None = None
        self.last_pitch_speed: float | None = None
        base = get_base_dir()
        data_path = (
            base
            / "data"
            / "MLB_avg"
            / "Average_Putouts_per_Game_by_Position__Last_5_Years_.csv"
        )
        self.target_putout_probs = load_putout_probabilities(data_path)
        self.outs_by_position: Dict[str, int] = {
            "P": 0,
            "C": 0,
            "1B": 0,
            "2B": 0,
            "3B": 0,
            "SS": 0,
            "LF": 0,
            "CF": 0,
            "RF": 0,
        }
        self.total_putouts = 0
        self.two_strike_counts = 0
        self.three_ball_counts = 0
        self.logged_strikeouts = 0
        self.logged_catcher_putouts = 0
        self._last_swing_strikeout = False

    # ------------------------------------------------------------------
    # Physics helper shims
    # ------------------------------------------------------------------
    def bat_impact(
        self, bat_speed: float, *, part: str = "sweet", rand: float | None = None
    ) -> tuple[float, float]:
        """Return exit velocity and power factor for a bat ``part``.

        Older versions of :class:`playbalance.physics.Physics` did not expose
        ``bat_impact``.  To remain compatible, this shim tries to use the
        method when available and otherwise falls back to the module level
        function.
        """

        if hasattr(self.physics, "bat_impact"):
            return self.physics.bat_impact(bat_speed, part=part, rand=rand)
        return bat_impact_func(
            self.config, bat_speed, part=part, rand=rand, rng=self.rng
        )

    # ------------------------------------------------------------------
    # Fatigue helpers
    # ------------------------------------------------------------------
    def _update_fatigue(self, state: PitcherState) -> None:
        remaining = state.player.endurance - state.pitches_thrown
        exhausted = self.config.get("pitcherExhaustedThresh", 0)
        tired = self.config.get("pitcherTiredThresh", 0)
        if remaining <= exhausted:
            state.player.fatigue = "exhausted"
        elif remaining <= tired:
            state.player.fatigue = "tired"
        else:
            state.player.fatigue = "fresh"

    def _fatigued_pitcher(self, pitcher: Pitcher) -> Pitcher:
        fatigue = getattr(pitcher, "fatigue", "fresh")
        pitch_mult = as_mult = co_mult = mo_mult = 1.0
        if fatigue == "tired":
            pitch_mult = self.config.get("tiredPitchRatPct", 100) / 100.0
            as_mult = self.config.get("tiredASPct", 100) / 100.0
            co_mult = self.config.get("effCOPct", 100) / 100.0
            mo_mult = self.config.get("effMOPct", 100) / 100.0
        elif fatigue == "exhausted":
            pitch_mult = self.config.get("exhaustedPitchRatPct", 100) / 100.0
            as_mult = self.config.get("exhaustedASPct", 100) / 100.0
            co_mult = self.config.get("effCOPct", 100) / 100.0
            mo_mult = self.config.get("effMOPct", 100) / 100.0
        scaled = replace(pitcher)
        for attr in PITCH_RATINGS:
            setattr(scaled, attr, int(getattr(pitcher, attr) * pitch_mult))
        scaled.arm = int(pitcher.arm * as_mult)
        scaled.control = int(pitcher.control * co_mult)
        scaled.movement = int(pitcher.movement * mo_mult)
        return scaled

    # ------------------------------------------------------------------
    # Stat helpers
    # ------------------------------------------------------------------
    def _add_stat(self, state: BatterState, attr: str, amount: int = 1) -> None:
        """Increment ``attr`` on ``state`` and the player's season totals."""

        setattr(state, attr, getattr(state, attr) + amount)
        season = getattr(state.player, "season_stats", None)
        if season is None:
            season = {}
            state.player.season_stats = season
        season[attr] = season.get(attr, 0) + amount

    def _add_fielding_stat(
        self,
        state: FieldingState,
        attr: str,
        amount: int = 1,
        *,
        position: str | None = None,
    ) -> None:
        """Increment ``attr`` on ``state`` and season totals.

        When recording a putout the credited position is tracked to allow
        comparison with MLB averages and to dynamically adjust fielding
        behaviour.
        """

        setattr(state, attr, getattr(state, attr) + amount)
        season = getattr(state.player, "season_stats", None)
        if season is None:
            season = {}
            state.player.season_stats = season
        season[attr] = season.get(attr, 0) + amount

        if attr == "po":
            pos = (position or getattr(state.player, "primary_position", "")).upper()
            if pos:
                self.outs_by_position[pos] = self.outs_by_position.get(pos, 0) + amount
                self.total_putouts += amount
                if pos == "C":
                    self.logged_catcher_putouts += amount
                self._adjust_fielding_config(pos)

    def _adjust_fielding_config(self, position: str) -> None:
        """Adjust fielding parameters to target MLB putout rates."""

        target = self.target_putout_probs.get(position)
        if not target or self.total_putouts == 0:
            return
        current = self.outs_by_position[position] / self.total_putouts
        diff = target - current
        if abs(diff) < 0.01:
            return
        mapping = {
            "P": "catchChancePitcherAdjust",
            "C": "catchChanceCatcherAdjust",
            "1B": "catchChanceFirstBaseAdjust",
            "2B": "catchChanceSecondBaseAdjust",
            "3B": "catchChanceThirdBaseAdjust",
            "SS": "catchChanceShortStopAdjust",
            "LF": "catchChanceLeftFieldAdjust",
            "CF": "catchChanceCenterFieldAdjust",
            "RF": "catchChanceRightFieldAdjust",
        }
        attr = mapping.get(position)
        if not attr:
            return
        current_adj = getattr(self.config, attr, 0.0)
        setattr(self.config, attr, current_adj + diff * 5)

    def _set_runner_leads(self, offense: TeamState) -> None:
        """Update lead state for runners on first or second base."""

        long_speed = self.config.get("longLeadSpeed", 70)
        for base in (0, 1):
            runner = offense.bases[base]
            if runner is None:
                continue
            runner.lead = 2 if runner.player.sp >= long_speed else 0

    def _maybe_pickoff(
        self,
        offense: TeamState,
        defense: TeamState,
        runner_state: BatterState,
        steal_chance: int,
    ) -> int:
        """Attempt a pickoff.  Returns the number of outs recorded."""

        if not self.defense.maybe_pickoff(
            steal_chance=steal_chance,
            lead=runner_state.lead,
            pitches_since=self.pitches_since_pickoff,
        ):
            return 0

        self.debug_log.append("Pickoff attempt")
        self.pitches_since_pickoff = 0

        pitcher_state = defense.current_pitcher_state
        if pitcher_state is None:
            return 0

        hold = pitcher_state.player.hold_runner
        speed = runner_state.player.sp
        success_prob = hold / max(1, hold + speed)
        balk_prob = 0.02
        outcome = self.rng.random()

        if outcome < success_prob:
            stealing = self.rng.random() < (steal_chance / 100.0)
            if stealing:
                self.debug_log.append("Runner picked off stealing")
                pitcher_state.pocs += 1
                self._add_stat(runner_state, "pocs")
            else:
                self.debug_log.append("Runner picked off")
                pitcher_state.pk += 1
                self._add_stat(runner_state, "po")
            offense.bases[0] = None
            offense.base_pitchers[0] = None
            return 1
        if outcome < success_prob + balk_prob:
            self.debug_log.append("Balk on pickoff")
            pitcher_state.bk += 1
            for base in range(2, -1, -1):
                runner = offense.bases[base]
                if runner is None:
                    continue
                ps_runner = offense.base_pitchers[base]
                if base == 2:
                    self._score_runner(offense, defense, 2)
                else:
                    offense.bases[base + 1] = runner
                    offense.base_pitchers[base + 1] = ps_runner
                offense.bases[base] = None
                offense.base_pitchers[base] = None
            return 0

        if (
            self.rng.random() < 0.1
            and runner_state.player.sp
            <= self.config.get("pickoffScareSpeed", 0)
        ):
            self.debug_log.append("Pickoff nearly succeeds")
            runner_state.lead = 0

        return 0

    def _get_fielder(self, defense: TeamState, position: str) -> Optional[FieldingState]:
        """Return the ``FieldingState`` for ``position`` if present."""

        for player in defense.lineup + defense.pitchers:
            if (
                player.primary_position == position
                or position in getattr(player, "other_positions", [])
            ):
                return defense.fielding_stats.setdefault(
                    player.player_id, FieldingState(player)
                )
        return None

    def _determine_infield_situation(
        self, offense: TeamState, defense: TeamState, outs: int
    ) -> str:
        """Return the infield alignment for the current situation."""

        if offense.bases[2] is not None:
            if abs(defense.runs - offense.runs) <= 1:
                return "guardLines"
            return "cutoffRun"
        if offense.bases[0] is not None and outs < 2:
            return "doublePlay"
        return "normal"

    def _set_defensive_alignment(
        self, offense: TeamState, defense: TeamState, outs: int
    ) -> None:
        """Determine and store the defensive alignment and positions."""

        batter = offense.lineup[offense.batting_index % len(offense.lineup)]
        self.current_infield_situation = self._determine_infield_situation(
            offense, defense, outs
        )
        self.current_outfield_situation = "normal"
        self.current_field_positions = self.defense.set_field_positions(
            pull=getattr(batter, "pl", 50), power=getattr(batter, "ph", 50)
        )
        self.debug_log.append(
            "Defensive alignment: infield="
            f"{self.current_infield_situation}, outfield="
            f"{self.current_outfield_situation}"
        )

    # ------------------------------------------------------------------
    # Pitcher state helpers
    # ------------------------------------------------------------------
    def _on_pitcher_enter(
        self, offense: TeamState, defense: TeamState, *, starting: bool = False
    ) -> None:
        """Record statistics when a pitcher enters the game."""

        ps = defense.current_pitcher_state
        if ps is None:
            return
        ps.g += 1
        if starting:
            ps.gs += 1
        fs = defense.fielding_stats.setdefault(ps.player.player_id, FieldingState(ps.player))
        fs.g += 1
        if starting:
            fs.gs += 1
        ps.ir += sum(1 for b in offense.bases if b is not None)
        lead = defense.runs - offense.runs
        if lead > 0 and lead <= 3:
            ps.svo += 1
            ps.in_save_situation = True
        else:
            ps.in_save_situation = False

    def _on_pitcher_exit(
        self,
        ps: PitcherState | None,
        offense: TeamState,
        defense: TeamState,
        *,
        game_finished: bool = False,
    ) -> None:
        """Update save/hold/blown save on pitcher exit."""

        if ps is None:
            return
        lead = defense.runs - offense.runs
        if ps.in_save_situation:
            if lead > 0:
                if game_finished:
                    ps.sv += 1
                    ps.gf += 1
                else:
                    if ps.outs > 0:
                        ps.hld += 1
            else:
                ps.bs += 1
        if game_finished and not ps.gf:
            ps.gf += 1
        ps.in_save_situation = False

    def _score_runner(
        self, offense: TeamState, defense: TeamState, base_idx: int
    ) -> None:
        """Handle a runner scoring from ``base_idx``."""

        runner = offense.bases[base_idx]
        if runner is None:
            return
        offense.runs += 1
        self._add_stat(runner, "r")
        # Pitcher on scoring team receives positive toast points
        scoring_pitcher = offense.current_pitcher_state
        if scoring_pitcher is not None:
            scoring_pitcher.toast += self.config.get("pitchScoringOffRun", 0)
        pitcher_for_runner = offense.base_pitchers[base_idx]
        if pitcher_for_runner is not None:
            pitcher_for_runner.r += 1
            pitcher_for_runner.er += 1
            pitcher_for_runner.toast += self.config.get("pitchScoringRun", 0)
            pitcher_for_runner.toast += self.config.get("pitchScoringER", 0)
            current = defense.current_pitcher_state
            if current is not None and current is not pitcher_for_runner:
                current.irs += 1
        offense.bases[base_idx] = None
        offense.base_pitchers[base_idx] = None

    # ------------------------------------------------------------------
    # Core loop helpers
    # ------------------------------------------------------------------
    def simulate_game(
        self, innings: int = 9, persist_stats: bool = True
    ) -> None:
        """Simulate a complete game.

        The game will extend into extra innings if tied after the requested
        number of innings and the bottom half of the final inning is skipped
        when the home team is already ahead. Only very small parts of a real
        baseball game are modelled – enough to exercise decision making
        paths for the tests.

        Set ``persist_stats`` to ``False`` to skip merging results into season
        totals or saving them to disk.
        """

        inning = 1
        if innings > 0:
            while True:
                # Top half
                self._play_half(self.away, self.home)
                if inning >= innings and self.away.runs < self.home.runs:
                    break
                # Bottom half
                self._play_half(self.home, self.away)
                if inning >= innings and self.home.runs != self.away.runs:
                    break
                inning += 1

        if persist_stats:
            # Finalize pitching stats for pitchers who finished the game
            self._on_pitcher_exit(
                self.home.current_pitcher_state,
                self.away,
                self.home,
                game_finished=True,
            )
            self._on_pitcher_exit(
                self.away.current_pitcher_state,
                self.home,
                self.away,
                game_finished=True,
            )

            for team in (self.home, self.away):
                for bs in team.lineup_stats.values():
                    season = getattr(bs.player, "season_stats", {})
                    for f in fields(BatterState):
                        if f.name == "player":
                            continue
                        season[f.name] = season.get(f.name, 0) + getattr(bs, f.name)
                    season_state = BatterState(bs.player)
                    for f in fields(BatterState):
                        if f.name == "player":
                            continue
                        setattr(season_state, f.name, season.get(f.name, 0))
                    season.update(compute_batting_derived(season_state))
                    season.update(compute_batting_rates(season_state))
                    season["2b"] = season.get("b2", 0)
                    season["3b"] = season.get("b3", 0)
                    bs.player.season_stats = season

                for ps in team.pitcher_stats.values():
                    season = getattr(ps.player, "season_stats", {})
                    for attr, value in vars(ps).items():
                        if attr in {"player", "in_save_situation"}:
                            continue
                        season[attr] = season.get(attr, 0) + value
                    season_state = PitcherState()
                    season_state.player = ps.player
                    for attr, value in season.items():
                        if attr in {"player", "in_save_situation"}:
                            continue
                        setattr(season_state, attr, value)
                    season.update(compute_pitching_derived(season_state))
                    season.update(compute_pitching_rates(season_state))
                    ps.player.season_stats = season

                for fs in team.fielding_stats.values():
                    season = getattr(fs.player, "season_stats", {})
                    for f in fields(FieldingState):
                        if f.name == "player":
                            continue
                        season[f.name] = season.get(f.name, 0) + getattr(fs, f.name)
                    season_state = FieldingState(fs.player)
                    for f in fields(FieldingState):
                        if f.name == "player":
                            continue
                        setattr(season_state, f.name, season.get(f.name, 0))
                    season.update(compute_fielding_derived(season_state))
                    season.update(compute_fielding_rates(season_state))
                    fs.player.season_stats = season

            for team, opp in ((self.home, self.away), (self.away, self.home)):
                derived = compute_team_derived(team, opp)
                season = team.team_stats
                season["g"] = season.get("g", 0) + 1
                season["r"] = season.get("r", 0) + team.runs
                season["ra"] = season.get("ra", 0) + opp.runs
                season["lob"] = season.get("lob", 0) + team.lob
                for key in (
                    "opp_pa",
                    "opp_h",
                    "opp_bb",
                    "opp_so",
                    "opp_hbp",
                    "opp_hr",
                    "opp_roe",
                ):
                    season[key] = season.get(key, 0) + derived[key]
                season.update(compute_team_rates(season))
                team.team_stats = season
                if team.team is not None:
                    team.team.season_stats = season

            players: Dict[str, Player] = {}
            for state in (self.home, self.away):
                for bs in state.lineup_stats.values():
                    players[bs.player.player_id] = bs.player
                for ps in state.pitcher_stats.values():
                    players[ps.player.player_id] = ps.player
                for fs in state.fielding_stats.values():
                    players[fs.player.player_id] = fs.player
            teams = [t.team for t in (self.home, self.away) if t.team is not None]
            save_stats(players.values(), teams)

    def _play_half(self, offense: TeamState, defense: TeamState) -> None:
        # Allow the defensive team to consider a late inning defensive swap
        inning = len(offense.inning_runs) + 1
        self.subs.maybe_defensive_sub(defense, inning, self.debug_log)

        start_runs = offense.runs
        start_log = len(self.debug_log)
        outs = 0
        plate_appearances = 0
        max_pa = self.config.get("maxHalfInningPA", 0)
        max_runs = self.config.get("maxHalfInningRuns", 0)
        limits_enabled = bool(self.config.get("halfInningLimitEnabled", 1))
        while outs < 3:
            if limits_enabled:
                if max_pa and plate_appearances >= max_pa:
                    self.debug_log.append(
                        f"Aborting half-inning after {plate_appearances} plate appearances "
                        f"(limit {max_pa})"
                    )
                    break
                runs_scored = offense.runs - start_runs
                if max_runs and runs_scored >= max_runs:
                    self.debug_log.append(
                        f"Aborting half-inning after {runs_scored} runs "
                        f"(limit {max_runs})"
                    )
                    break
            self.current_outs = outs
            self._set_defensive_alignment(offense, defense, outs)
            outs += self.play_at_bat(offense, defense)
            plate_appearances += 1
        inning_events = self.debug_log[start_log:]
        for runner in offense.bases:
            if runner is not None:
                self._add_stat(runner, "lob")
        lob = sum(1 for r in offense.bases if r is not None)
        offense.lob += lob
        offense.inning_lob.append(lob)
        offense.inning_events.append(inning_events)
        offense.bases = [None, None, None]
        offense.base_pitchers = [None, None, None]
        offense.inning_runs.append(offense.runs - start_runs)
        # Award toast points for completing innings after the 4th
        if inning > 4 and defense.current_pitcher_state is not None:
            defense.current_pitcher_state.toast += self.config.get(
                "pitchScoringInnsAfter4", 0
            )

    def play_at_bat(self, offense: TeamState, defense: TeamState) -> int:
        """Play a single at-bat.  Returns the number of outs recorded."""
        inning = len(offense.inning_runs) + 1
        run_diff = offense.runs - defense.runs
        home_team = defense is self.home
        self.subs.maybe_warm_reliever(
            defense, inning=inning, run_diff=run_diff, home_team=home_team
        )
        old_pitcher = defense.current_pitcher_state
        changed = self.subs.maybe_replace_pitcher(
            defense,
            inning=inning,
            run_diff=run_diff,
            home_team=home_team,
            log=self.debug_log,
        )
        if changed:
            self._on_pitcher_exit(old_pitcher, offense, defense)
            self._on_pitcher_enter(offense, defense)

        # Check if any existing runner should be replaced with a pinch runner
        for base_idx, runner in enumerate(offense.bases):
            if runner is not None:
                self.subs.maybe_pinch_run(
                    offense,
                    base=base_idx,
                    inning=inning,
                    outs=self.current_outs,
                    run_diff=run_diff,
                    log=self.debug_log,
                )

        self._set_runner_leads(offense)

        # Defensive decisions prior to the at-bat.  These mostly log the
        # outcome for manual inspection in the exhibition dialog.  The
        # simplified simulation does not yet modify gameplay based on them.
        runner_state = offense.bases[0]
        runner = runner_state.player if runner_state else None
        holding_runner = False
        steal_chance = 0
        outs_from_pick = 0
        pitcher_fa = (
            defense.current_pitcher_state.player.fa
            if defense.current_pitcher_state
            else 0
        )
        first_fa = next(
            (p.fa for p in defense.lineup if p.primary_position == "1B"), 0
        )
        third_fa = next(
            (p.fa for p in defense.lineup if p.primary_position == "3B"), 0
        )
        charge_first, charge_third = self.defense.maybe_charge_bunt(
            pitcher_fa=pitcher_fa,
            first_fa=first_fa,
            third_fa=third_fa,
            on_first=offense.bases[0] is not None,
            on_second=offense.bases[1] is not None,
            on_third=offense.bases[2] is not None,
        )
        if charge_first or charge_third:
            self.debug_log.append("Defense charges bunt")
        outs_before = self.current_outs
        next_batter_ch = offense.lineup[
            offense.batting_index % len(offense.lineup)
        ].ch
        run_diff = offense.runs - defense.runs
        if runner_state and self.defense.maybe_hold_runner(runner.sp):
            holding_runner = True
            self.debug_log.append("Defense holds runner")
            pitcher_state = defense.current_pitcher_state
            if pitcher_state is not None:
                self._update_fatigue(pitcher_state)
                pitcher = self._fatigued_pitcher(pitcher_state.player)
                steal_chance = int(
                    self.offense.calculate_steal_chance(
                        balls=0,
                        strikes=0,
                        runner_sp=runner.sp,
                        pitcher_hold=pitcher.hold_runner,
                        pitcher_is_left=pitcher.bats == "L",
                        pitcher_is_wild=pitcher.control <= 30,
                        pitcher_in_windup=False,
                        outs=outs_before,
                        runner_on=1,
                        batter_ch=next_batter_ch,
                        run_diff=run_diff,
                    )
                    * 100
                )
            outs_from_pick = self._maybe_pickoff(
                offense, defense, runner_state, steal_chance
            )
            self.current_outs += outs_from_pick
            outs_before += outs_from_pick

        inning = len(offense.inning_runs) + 1
        batter_idx = offense.batting_index % len(offense.lineup)
        pitcher_batting = (
            offense.current_pitcher_state is not None
            and offense.lineup[batter_idx].player_id
            == offense.current_pitcher_state.player.player_id
        )
        if pitcher_batting:
            old_off_pitcher = offense.current_pitcher_state
            batter = self.subs.maybe_pinch_hit_for_pitcher(
                offense,
                defense,
                batter_idx,
                inning=inning,
                outs=outs_before,
                log=self.debug_log,
            )
            offense.batting_index += 1
            if batter.player_id != old_off_pitcher.player.player_id:
                self._on_pitcher_exit(old_off_pitcher, defense, offense)
                self._on_pitcher_enter(defense, offense)
        else:
            old_pitcher = defense.current_pitcher_state
            batter = self.subs.maybe_double_switch(
                offense, defense, batter_idx, self.debug_log
            )
            if batter is not None:
                self._on_pitcher_exit(old_pitcher, offense, defense)
                self._on_pitcher_enter(offense, defense)
            else:
                starter = offense.lineup[batter_idx]
                if run_diff < 0:
                    on_deck_idx = (batter_idx + 1) % len(offense.lineup)
                    batter = self.subs.maybe_pinch_hit_need_run(
                        offense,
                        defense,
                        batter_idx,
                        on_deck_idx,
                        inning=inning,
                        outs=outs_before,
                        run_diff=run_diff,
                        home_team=offense is self.home,
                        log=self.debug_log,
                    )
                    if batter is starter:
                        batter = self.subs.maybe_pinch_hit_need_hit(
                            offense,
                            batter_idx,
                            on_deck_idx,
                            inning=inning,
                            outs=outs_before,
                            run_diff=run_diff,
                            home_team=offense is self.home,
                            log=self.debug_log,
                        )
                else:
                    batter = starter
                if batter is starter:
                    batter = self.subs.maybe_pinch_hit(
                        offense, batter_idx, self.debug_log
                    )
            offense.batting_index += 1
        on_deck_idx = offense.batting_index % len(offense.lineup)
        on_deck = offense.lineup[on_deck_idx]

        on_first = offense.bases[0] is not None
        on_second = offense.bases[1] is not None
        on_third = offense.bases[2] is not None
        pitch_around, ibb = self.defense.maybe_pitch_around(
            inning=inning,
            batter_ph=batter.ph,
            batter_ch=batter.ch,
            on_deck_ph=on_deck.ph,
            on_deck_ch=on_deck.ch,
            batter_gf=batter.gf,
            on_deck_gf=on_deck.gf,
            outs=outs_before,
            on_first=on_first,
            on_second=on_second,
            on_third=on_third,
        )
        if ibb:
            self.debug_log.append("Intentional walk issued")
        elif pitch_around:
            self.debug_log.append("Pitch around")

        batter_state = offense.lineup_stats.setdefault(
            batter.player_id, BatterState(batter)
        )
        pitcher_state = defense.current_pitcher_state
        if pitcher_state is None:
            raise RuntimeError("Defense has no available pitcher")

        pitcher_state.bf += 1
        start_pitches = pitcher_state.pitches_thrown

        # Record plate appearance
        self._add_stat(batter_state, "pa")
        season_pitcher = getattr(pitcher_state.player, "season_stats", None)
        if season_pitcher is None:
            pitcher_state.player.season_stats = {}

        outs = 0
        balls = 0
        strikes = 0
        seen_two_strike = False
        seen_three_ball = False

        if ibb:
            self._add_stat(batter_state, "bb")
            self._add_stat(batter_state, "ibb")
            pitcher_state.bb += 1
            pitcher_state.ibb += 1
            pitcher_state.toast += self.config.get("pitchScoringWalk", 0)
            pitcher_state.consecutive_hits = 0
            pitcher_state.consecutive_baserunners += 1
            self._advance_walk(offense, defense, batter_state)
            self._add_stat(
                batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
            )
            pitcher_state.outs += outs
            return outs + outs_from_pick

        inning = len(offense.inning_runs) + 1
        run_diff = offense.runs - defense.runs

        while True:
            if not seen_two_strike and strikes >= 2:
                seen_two_strike = True
                self.two_strike_counts += 1
            if not seen_three_ball and balls >= 3:
                seen_three_ball = True
                self.three_ball_counts += 1

            self._update_fatigue(pitcher_state)
            pitcher = self._fatigued_pitcher(pitcher_state.player)
            self._set_runner_leads(offense)
            runner_state = offense.bases[0]
            if runner_state:
                hit_run_chance = int(
                    self.offense.calculate_hit_and_run_chance(
                        runner_sp=runner_state.player.sp,
                        batter_ch=batter.ch,
                        batter_ph=batter.ph,
                        balls=balls,
                        strikes=strikes,
                        run_diff=run_diff,
                        runners_on_first_and_second=(offense.bases[1] is not None),
                        pitcher_wild=pitcher.control <= 30,
                    )
                    * 100
                )
                if holding_runner and self.defense.maybe_pitch_out(
                    steal_chance=steal_chance,
                    hit_run_chance=hit_run_chance,
                    ball_count=balls,
                    inning=inning,
                    is_home_team=(defense is self.home),
                ):
                    self.debug_log.append("Pitch out")
                if self.offense.maybe_hit_and_run(
                    runner_sp=runner_state.player.sp,
                    batter_ch=batter.ch,
                    batter_ph=batter.ph,
                    balls=balls,
                    strikes=strikes,
                    run_diff=run_diff,
                    runners_on_first_and_second=(offense.bases[1] is not None),
                    pitcher_wild=pitcher.control <= 30,
                ):
                    self.debug_log.append("Hit and run")
                    steal_result = self._attempt_steal(
                        offense,
                        defense,
                        pitcher_state.player,
                        force=True,
                        balls=balls,
                        strikes=strikes,
                        outs=outs,
                        runner_on=1,
                        batter_ch=batter.ch,
                        pitcher_is_wild=pitcher.control <= 30,
                        pitcher_in_windup=False,
                        run_diff=run_diff,
                    )
                    if steal_result is False:
                        outs += 1
                elif balls == 0 and strikes == 0 and self.offense.maybe_sacrifice_bunt(
                    batter_is_pitcher=batter.primary_position == "P",
                    batter_ch=batter.ch,
                    batter_ph=batter.ph,
                    on_deck_ch=on_deck.ch,
                    on_deck_ph=on_deck.ph,
                    outs=outs_before,
                    inning=inning,
                    on_first=offense.bases[0] is not None,
                    on_second=offense.bases[1] is not None,
                    run_diff=run_diff,
                ):
                    self.debug_log.append("Sacrifice bunt")
                    b = offense.bases
                    bp = offense.base_pitchers
                    runs_scored = 0
                    if b[2]:
                        self._score_runner(offense, defense, 2)
                        runs_scored += 1
                    if b[1]:
                        offense.bases[2] = b[1]
                        offense.base_pitchers[2] = bp[1]
                        offense.bases[1] = None
                        offense.base_pitchers[1] = None
                    if b[0]:
                        offense.bases[1] = b[0]
                        offense.base_pitchers[1] = bp[0]
                        offense.bases[0] = None
                        offense.base_pitchers[0] = None
                    self._add_stat(batter_state, "sh")
                    if runs_scored:
                        self._add_stat(batter_state, "rbi", runs_scored)
                    outs += 1
                    self._add_stat(
                        batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
                    )
                    pitcher_state.outs += outs
                    return outs + outs_from_pick

            if (
                offense.bases[2]
                and balls == 0
                and strikes == 0
                and self.offense.maybe_suicide_squeeze(
                    batter_ch=batter.ch,
                    batter_ph=batter.ph,
                    balls=balls,
                    strikes=strikes,
                    runner_on_third_sp=offense.bases[2].player.sp,
                )
            ):
                self.debug_log.append("Suicide squeeze")
                if offense.bases[2]:
                    self._score_runner(offense, defense, 2)
                self._add_stat(batter_state, "sh")
                self._add_stat(batter_state, "rbi")
                outs += 1
                self._add_stat(
                    batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
                )
                pitcher_state.outs += outs
                return outs + outs_from_pick

            target_pitches = self.config.get("targetPitchesPerPA", 0)
            strike_rate = float(self.config.get("leagueStrikePct", 65.9)) / 100.0
            pitches_this_pa = pitcher_state.pitches_thrown - start_pitches
            if target_pitches and pitches_this_pa < target_pitches:
                desired_total = int(target_pitches)
                if self.rng.random() < target_pitches - desired_total:
                    desired_total += 1
                extra_pitches = max(0, desired_total - pitches_this_pa - 1)
                for _ in range(extra_pitches):
                    pitcher_state.pitches_thrown += 1
                    self.pitches_since_pickoff = min(
                        self.pitches_since_pickoff + 1, 4
                    )
                    if self.rng.random() < strike_rate:
                        pitcher_state.strikes_thrown += 1
                    else:
                        pitcher_state.balls_thrown += 1

            pitcher_state.pitches_thrown += 1
            self.pitches_since_pickoff = min(self.pitches_since_pickoff + 1, 4)
            pitch_type, _ = self.pitcher_ai.select_pitch(
                pitcher, balls=balls, strikes=strikes
            )
            loc_r = self.rng.random()
            pitch_speed = self.physics.pitch_velocity(
                pitch_type, pitcher.arm, rand=loc_r
            )
            control_scale = self.config.controlScale
            jitter = self.rng.uniform(-5, 5)
            control_chance = (pitcher.control + jitter) / control_scale
            control_chance = max(0.0, min(1.0, control_chance))
            width, height = self.physics.control_box(pitch_type)
            frac = loc_r
            miss_amt = 0.0
            if loc_r >= control_chance:
                miss_amt = (loc_r - control_chance) * 100.0
                miss_amt += self.rng.uniform(0.0, miss_amt)
                width, height = self.physics.expand_control_box(width, height, miss_amt)
            x_off = (frac * 2 - 1) * width
            y_off = (frac * 2 - 1) * height
            exp_dx, exp_dy = self.physics.pitch_break(pitch_type, rand=0.5)
            x_off -= exp_dx
            y_off -= exp_dy
            dx, dy = self.physics.pitch_break(pitch_type, rand=loc_r)
            x_off += dx
            y_off += dy
            dist = int(round(max(abs(x_off), abs(y_off))))
            plate_w = getattr(self.config, "plateWidth", 3)
            plate_h = getattr(self.config, "plateHeight", 3)
            in_zone = dist <= max(plate_w, plate_h)
            dec_r = self.rng.random()
            if miss_amt:
                pitch_speed = self.physics.reduce_pitch_velocity_for_miss(
                    pitch_speed, miss_amt, rand=dec_r
                )
            self.last_pitch_speed = pitch_speed
            swing, contact_quality = self.batter_ai.decide_swing(
                batter,
                pitcher,
                pitch_type=pitch_type,
                balls=balls,
                strikes=strikes,
                dist=dist,
                dx=x_off,
                dy=y_off,
                random_value=dec_r,
            )
            contact = getattr(self.batter_ai, "last_contact", contact_quality > 0)
            catcher_fs = self._get_fielder(defense, "C")
            if swing and self._maybe_catcher_interference(
                offense,
                defense,
                batter_state,
                catcher_fs,
                pitcher_state,
                start_pitches,
            ):
                pitcher_state.record_pitch(in_zone=in_zone, swung=True, contact=False)
                pitcher_state.outs += outs
                return outs + outs_from_pick

            pitcher_state.record_pitch(in_zone=in_zone, swung=swing, contact=contact)

            if swing:
                self.infield_fly = False
                out_of_zone = not in_zone
                if (
                    contact
                    and out_of_zone
                    and self.rng.random()
                    >= self.config.get("outOfZoneContactHitChance", 0.1)
                ):
                    pitcher_state.balls_thrown += 1
                    self._add_stat(batter_state, "ab")
                    outs += 1
                    pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                    pitcher_state.consecutive_hits = 0
                    pitcher_state.consecutive_baserunners = 0
                    self._add_stat(
                        batter_state,
                        "pitches",
                        pitcher_state.pitches_thrown - start_pitches,
                    )
                    pitcher_state.outs += outs
                    run_diff = offense.runs - defense.runs
                    self.subs.maybe_warm_reliever(
                        defense,
                        inning=inning,
                        run_diff=run_diff,
                        home_team=home_team,
                    )
                    return outs + outs_from_pick

                contact_quality_var = contact_quality
                if contact and out_of_zone:
                    contact_quality_var = max(0.1, contact_quality_var * 0.25)
                bases, error = self._swing_result(
                    batter,
                    pitcher,
                    defense,
                    batter_state,
                    pitcher_state,
                    pitch_speed=pitch_speed,
                    contact_quality=contact_quality_var,
                    is_third_strike=strikes >= 2,
                )
                if self._last_swing_strikeout:
                    if in_zone:
                        pitcher_state.strikes_thrown += 1
                    else:
                        pitcher_state.balls_thrown += 1
                    self._add_stat(batter_state, "ab")
                    self._add_stat(batter_state, "so")
                    self._add_stat(batter_state, "so_swinging")
                    pitcher_state.so += 1
                    pitcher_state.so_swinging += 1
                    outs += 1
                    pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                    pitcher_state.toast += self.config.get("pitchScoringStrikeOut", 0)
                    pitcher_state.consecutive_hits = 0
                    pitcher_state.consecutive_baserunners = 0
                    p_fs = defense.fielding_stats.get(
                        pitcher_state.player.player_id
                    )
                    if p_fs:
                        self._add_fielding_stat(p_fs, "a")
                    self._add_stat(
                        batter_state,
                        "pitches",
                        pitcher_state.pitches_thrown - start_pitches,
                    )
                    pitcher_state.outs += outs
                    run_diff = offense.runs - defense.runs
                    self.subs.maybe_warm_reliever(
                        defense, inning=inning, run_diff=run_diff, home_team=home_team
                    )
                    return outs + outs_from_pick
                if self.infield_fly:
                    if in_zone:
                        pitcher_state.strikes_thrown += 1
                    else:
                        pitcher_state.balls_thrown += 1
                    self._add_stat(batter_state, "ab")
                    outs += 1
                    pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                    pitcher_state.consecutive_hits = 0
                    pitcher_state.consecutive_baserunners = 0
                    self._add_stat(
                        batter_state,
                        "pitches",
                        pitcher_state.pitches_thrown - start_pitches,
                    )
                    pitcher_state.outs += outs
                    run_diff = offense.runs - defense.runs
                    self.subs.maybe_warm_reliever(
                        defense, inning=inning, run_diff=run_diff, home_team=home_team
                    )
                    return outs + outs_from_pick
                if bases == 0:
                    if in_zone:
                        pitcher_state.strikes_thrown += 1
                    else:
                        pitcher_state.balls_thrown += 1
                    self._add_stat(batter_state, "ab")
                    outs += 1
                    if (
                        self.last_batted_ball_type == "ground"
                        and offense.bases[0] is not None
                    ):
                        if self.rng.random() < self.config.get("doublePlayProb", 0):
                            outs += 1
                            self._add_stat(batter_state, "gidp")
                            offense.bases[0] = None
                            offense.base_pitchers[0] = None
                        else:
                            offense.bases[1] = offense.bases[0]
                            offense.base_pitchers[1] = offense.base_pitchers[0]
                            offense.bases[0] = None
                            offense.base_pitchers[0] = None
                    pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                    pitcher_state.consecutive_hits = 0
                    pitcher_state.consecutive_baserunners = 0
                    self._add_stat(
                        batter_state,
                        "pitches",
                        pitcher_state.pitches_thrown - start_pitches,
                    )
                    pitcher_state.outs += outs
                    run_diff = offense.runs - defense.runs
                    self.subs.maybe_warm_reliever(
                        defense, inning=inning, run_diff=run_diff, home_team=home_team
                    )
                    return outs + outs_from_pick
                if bases:
                    if in_zone:
                        pitcher_state.strikes_thrown += 1
                    else:
                        pitcher_state.balls_thrown += 1
                    self._add_stat(batter_state, "ab")
                    if error:
                        pitcher_state.consecutive_hits = 0
                        pitcher_state.consecutive_baserunners += 1
                        outs_made = self._advance_runners(
                            offense,
                            defense,
                            batter_state,
                            bases=bases,
                            error=True,
                        )
                        if outs_made:
                            outs += outs_made
                            pitcher_state.toast += self.config.get(
                                "pitchScoringOut", 0
                            ) * outs_made
                            pitcher_state.consecutive_hits = 0
                            pitcher_state.consecutive_baserunners = 0
                            pitcher_state.outs += outs_made
                    else:
                        pitcher_state.h += 1
                        self._add_stat(batter_state, "h")
                        if bases == 4:
                            pitcher_state.hr += 1
                            pitcher_state.allowed_hr = True
                            self._add_stat(batter_state, "hr")
                        elif bases == 3:
                            pitcher_state.b3 += 1
                            self._add_stat(batter_state, "b3")
                        elif bases == 2:
                            pitcher_state.b2 += 1
                            self._add_stat(batter_state, "b2")
                        else:
                            pitcher_state.b1 += 1
                            self._add_stat(batter_state, "b1")
                        pitcher_state.toast += self.config.get(
                            "pitchScoringHit", 0
                        )
                        if pitcher_state.consecutive_hits:
                            pitcher_state.toast += self.config.get(
                                "pitchScoringConsHit", 0
                            )
                        pitcher_state.consecutive_hits += 1
                        pitcher_state.consecutive_baserunners += 1
                        outs_made = self._advance_runners(
                            offense, defense, batter_state, bases=bases
                        )
                        if outs_made:
                            outs += outs_made
                            pitcher_state.toast += self.config.get(
                                "pitchScoringOut", 0
                            ) * outs_made
                            pitcher_state.consecutive_hits = 0
                            pitcher_state.consecutive_baserunners = 0
                            pitcher_state.outs += outs_made
                    steal_result = self._attempt_steal(
                        offense,
                        defense,
                        pitcher_state.player,
                        batter=batter,
                        balls=balls,
                        strikes=strikes,
                        outs=outs,
                        runner_on=2,
                        batter_ch=batter.ch,
                        pitcher_is_wild=pitcher.control <= 30,
                        pitcher_in_windup=False,
                        run_diff=run_diff,
                    )
                    if steal_result is False:
                        outs += 1
                        pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                        pitcher_state.consecutive_hits = 0
                        pitcher_state.consecutive_baserunners = 0
                    steal_result = self._attempt_steal(
                        offense,
                        defense,
                        pitcher_state.player,
                        batter=batter,
                        balls=balls,
                        strikes=strikes,
                        outs=outs,
                        runner_on=1,
                        batter_ch=batter.ch,
                        pitcher_is_wild=pitcher.control <= 30,
                        pitcher_in_windup=False,
                        run_diff=run_diff,
                    )
                    if steal_result is False:
                        outs += 1
                        pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                        pitcher_state.consecutive_hits = 0
                        pitcher_state.consecutive_baserunners = 0
                    self._add_stat(
                        batter_state,
                        "pitches",
                        pitcher_state.pitches_thrown - start_pitches,
                    )
                    pitcher_state.outs += outs
                    run_diff = offense.runs - defense.runs
                    self.subs.maybe_warm_reliever(
                        defense, inning=inning, run_diff=run_diff, home_team=home_team
                    )
                    return outs + outs_from_pick
                foul_chance = self._foul_probability(
                    batter, pitcher, dist=dist, misread=self.batter_ai.last_misread
                )
                if contact and self.rng.random() < foul_chance:
                    if not in_zone:
                        pitcher_state.balls_thrown += 1
                    pitcher_state.strikes_thrown += 1
                    if self._attempt_foul_catch(
                        batter,
                        pitcher,
                        defense,
                        pitch_speed=pitch_speed,
                        rand=dec_r,
                    ):
                        self._add_stat(batter_state, "ab")
                        outs += 1
                        pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                        pitcher_state.consecutive_hits = 0
                        pitcher_state.consecutive_baserunners = 0
                        self._add_stat(
                            batter_state,
                            "pitches",
                            pitcher_state.pitches_thrown - start_pitches,
                        )
                        pitcher_state.outs += outs
                        run_diff = offense.runs - defense.runs
                        self.subs.maybe_warm_reliever(
                            defense,
                            inning=inning,
                            run_diff=run_diff,
                            home_team=home_team,
                        )
                        return outs + outs_from_pick
                    if strikes < 2:
                        strikes += 1
                    continue
                strikes += 1
                if not in_zone:
                    pitcher_state.balls_thrown += 1
                else:
                    pitcher_state.strikes_thrown += 1
            else:
                if in_zone:
                    strikes += 1
                    pitcher_state.strikes_thrown += 1
                else:
                    hbp_dist = self.config.get("closeBallDist", 5) + self.rng.randint(1, 2)
                    league_hbp = self.config.get("leagueHBPPerGame", 0.86)
                    if league_hbp > 0:
                        hbp_dist = int(round(hbp_dist * 0.86 / league_hbp))
                    if dist >= hbp_dist:
                        base_hbp = self.config.get("hbpBaseChance", 0.0)
                        step_out_chance = (
                            self.config.get("hbpBatterStepOutChance", 0) / 100.0
                        )
                        roll = self.rng.random()
                        if roll < base_hbp:
                            is_hbp = True
                        elif self.rng.random() < step_out_chance:
                            is_hbp = False
                        else:
                            is_hbp = True
                        if not is_hbp:
                            balls += 1
                            pitcher_state.balls_thrown += 1
                        else:
                            self._add_stat(batter_state, "hbp")
                            pitcher_state.hbp += 1
                            pitcher_state.toast += self.config.get(
                                "pitchScoringWalk", 0
                            )
                            pitcher_state.consecutive_hits = 0
                            pitcher_state.consecutive_baserunners += 1
                            self._advance_walk(offense, defense, batter_state)
                            self._add_stat(
                                batter_state,
                                "pitches",
                                pitcher_state.pitches_thrown - start_pitches,
                            )
                            pitcher_state.outs += outs
                            run_diff = offense.runs - defense.runs
                            self.subs.maybe_warm_reliever(
                                defense,
                                inning=inning,
                                run_diff=run_diff,
                                home_team=home_team,
                            )
                            return outs + outs_from_pick
                    else:
                        balls += 1
                        pitcher_state.balls_thrown += 1

            self._maybe_passed_ball(offense, defense, catcher_fs)

            if not seen_two_strike and strikes >= 2:
                seen_two_strike = True
                self.two_strike_counts += 1
            if not seen_three_ball and balls >= 3:
                seen_three_ball = True
                self.three_ball_counts += 1

            if balls >= 4:
                self._add_stat(batter_state, "bb")
                pitcher_state.bb += 1
                pitcher_state.toast += self.config.get("pitchScoringWalk", 0)
                pitcher_state.consecutive_hits = 0
                pitcher_state.consecutive_baserunners += 1
                self._advance_walk(offense, defense, batter_state)
                self._add_stat(
                    batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
                )
                pitcher_state.outs += outs
                run_diff = offense.runs - defense.runs
                self.subs.maybe_warm_reliever(
                    defense, inning=inning, run_diff=run_diff, home_team=home_team
                )
                return outs + outs_from_pick
            if strikes >= 3:
                self.logged_strikeouts += 1
                self._add_stat(batter_state, "ab")
                self._add_stat(batter_state, "so")
                if swing:
                    self._add_stat(batter_state, "so_swinging")
                    pitcher_state.so_swinging += 1
                else:
                    self._add_stat(batter_state, "so_looking")
                    pitcher_state.so_looking += 1
                pitcher_state.so += 1
                outs += 1
                pitcher_state.toast += self.config.get("pitchScoringOut", 0)
                pitcher_state.toast += self.config.get("pitchScoringStrikeOut", 0)
                pitcher_state.consecutive_hits = 0
                pitcher_state.consecutive_baserunners = 0
                catcher_fs = self._get_fielder(defense, "C")
                if catcher_fs:
                    self._add_fielding_stat(catcher_fs, "po", position="C")
                p_fs = defense.fielding_stats.get(pitcher_state.player.player_id)
                if p_fs:
                    self._add_fielding_stat(p_fs, "a")
                self._add_stat(
                    batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
                )
                pitcher_state.outs += outs
                run_diff = offense.runs - defense.runs
                self.subs.maybe_warm_reliever(
                    defense, inning=inning, run_diff=run_diff, home_team=home_team
                )
                return outs + outs_from_pick


    # ------------------------------------------------------------------
    # Pinch hitting
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Swing outcome
    # ------------------------------------------------------------------
    def _foul_probability(
        self,
        batter: Player,
        pitcher: Pitcher,
        *,
        dist: float = 0.0,
        misread: bool = False,
    ) -> float:
        """Return foul ball probability derived from configuration and ratings.

        ``foulPitchBasePct`` is the league-wide percentage of pitches that end
        in a foul ball while ``foulStrikeBasePct`` expresses that rate on a
        per-strike basis (~36% of strikes become fouls). ``ballInPlayPitchPct``
        represents the share of all pitches put in play and is used together
        with ``foulPitchBasePct`` to determine the overall contact rate. The
        resulting conversion yields roughly half of contacted pitches as balls
        in play and preserves the strike-based foul percentage without forcing
        a 1:1 split.

        ``foulContactTrendPct`` adds roughly ``+1.5`` percentage points for
        every 20 point edge in batter contact over pitcher movement. ``dist``
        allows far out-of-zone pitches to reduce foul likelihood while
        ``misread`` boosts the chance so complete misreads produce foul tips
        instead of whiffs.
        """

        cfg = self.config
        strike_base_pct = float(cfg.get("foulStrikeBasePct", 36.4))
        pitch_base_pct = float(cfg.get("foulPitchBasePct", 24.0)) / 100.0
        bip_pitch_pct = float(cfg.get("ballInPlayPitchPct", 25.0)) / 100.0
        trend_pct = float(cfg.get("foulContactTrendPct", 1.5))

        # Convert strike-based foul percentage to per-pitch using league strike
        # rate derived from the base configuration
        strike_rate = pitch_base_pct / (strike_base_pct / 100.0) if strike_base_pct else 0.0

        contact_delta = getattr(batter, "ch", 50) - getattr(pitcher, "movement", 50)
        foul_pct = strike_base_pct + (contact_delta / 20.0) * trend_pct
        foul_pct = max(0.0, min(95.0, foul_pct))

        foul_per_pitch = strike_rate * (foul_pct / 100.0)
        contact_rate = foul_per_pitch + bip_pitch_pct
        prob = foul_per_pitch / contact_rate if contact_rate > 0 else 0.0

        if dist > 0:
            prob *= max(0.0, 1.0 - dist * 0.1)
        if misread:
            prob *= 1.5

        return max(0.0, min(1.0, prob))

    def _attempt_foul_catch(
        self,
        batter: Player,
        pitcher: Pitcher,
        defense: TeamState,
        *,
        pitch_speed: float,
        rand: float,
        swing_type: str = "normal",
    ) -> bool:
        """Return ``True`` if a foul ball is caught for an out."""

        bat_speed = self.physics.bat_speed(
            batter.ph, swing_type=swing_type, pitch_speed=pitch_speed
        )
        bat_speed, _ = self.bat_impact(bat_speed, rand=rand)
        swing_angle = self.physics.swing_angle(batter.gf, swing_type=swing_type)
        vert_angle = self.physics.vertical_hit_angle(
            swing_type=swing_type, gf=batter.gf
        )
        vx, vy, vz = self.physics.launch_vector(
            getattr(batter, "ph", 50),
            getattr(batter, "pl", 50),
            swing_angle,
            vert_angle,
            swing_type=swing_type,
        )
        x, y, hang_time = self.physics.landing_point(vx, vy, vz)
        if self.rng.random() < 0.5:
            x = -abs(x)
        else:
            y = -abs(y)
        landing_dist = math.hypot(x, y)

        fielders = {p.primary_position.upper(): p for p in defense.lineup}
        fielders["P"] = pitcher
        for pos, (fx, fy) in DEFAULT_POSITIONS.items():
            fielder = fielders.get(pos)
            if not fielder:
                continue
            sp = getattr(fielder, "sp", 50)
            fa = getattr(fielder, "fa", 50)
            distance = math.hypot(fx - x, fy - y)
            run_time = (
                distance / self.physics.player_speed(sp)
                + self.physics.reaction_delay(pos, fa)
            )
            action = self.fielding_ai.catch_action(
                hang_time,
                run_time,
                position=pos,
                distance=distance,
                dist_from_home=landing_dist,
            )
            if action == "no_attempt":
                continue
            if self.fielding_ai.resolve_fly_ball(pos, fa, hang_time, action):
                fs = defense.fielding_stats.setdefault(
                    fielder.player_id, FieldingState(fielder)
                )
                self._add_fielding_stat(fs, "po", position=pos)
                self.debug_log.append("Foul ball caught")
                return True
        return False

    def _swing_result(
        self,
        batter: Player,
        pitcher: Pitcher,
        defense: TeamState,
        batter_state: BatterState,
        pitcher_state: PitcherState,
        *,
        pitch_speed: float,
        contact_quality: float = 1.0,
        swing_type: str = "normal",
        is_third_strike: bool = False,
    ) -> tuple[Optional[int], bool]:
        self._last_swing_strikeout = False
        if contact_quality <= 0:
            if is_third_strike:
                self._last_swing_strikeout = True
                self.logged_strikeouts += 1
                catcher_fs = self._get_fielder(defense, "C")
                if catcher_fs:
                    self._add_fielding_stat(catcher_fs, "po", position="C")
            return None, False
        bat_speed = self.physics.bat_speed(
            batter.ph, swing_type=swing_type, pitch_speed=pitch_speed
        )
        bat_speed, _ = self.bat_impact(bat_speed)
        # Calculate and store angles for potential future physics steps.
        swing_angle = self.physics.swing_angle(batter.gf, swing_type=swing_type)
        vert_base = abs(
            self.physics.vertical_hit_angle(swing_type=swing_type, gf=batter.gf)
        )
        power_adjust = (getattr(batter, "ph", 50) - 50) * 0.1
        # ------------------------------------------------------------------
        # Determine batted ball distribution.  Baseline rates are pulled from
        # configuration but are modified by player and pitcher attributes.
        # Sluggers with loft in their swings should generate more fly balls,
        # while pitchers with strong movement tend to induce more grounders.
        # Each component is weighted so the impact can be tuned through
        # ``PlayBalance`` configuration.
        # ------------------------------------------------------------------
        base_gb = self.config.ground_ball_base_rate
        base_ld = self.config.line_drive_base_rate
        base_fb = self.config.fly_ball_base_rate
        power_factor = (
            getattr(batter, "ph", 50) - 50
        ) * self.config.bip_power_weight
        launch_factor = (
            getattr(batter, "gf", 50) - 50
        ) * self.config.bip_launch_weight
        movement_factor = (
            getattr(pitcher, "movement", 50) - 50
        ) * self.config.bip_movement_weight
        gb = base_gb - power_factor - launch_factor + movement_factor
        fb = base_fb + power_factor + launch_factor - movement_factor
        gb = max(0.0, gb)
        fb = max(0.0, fb)
        ld = max(0.0, base_gb + base_ld + base_fb - gb - fb)
        total = max(1.0, gb + ld + fb)
        roll = self.rng.random() * total
        if roll < gb:
            vert_angle = -abs(vert_base + swing_angle + power_adjust + 1)
            outcome = "ground"
        elif roll < gb + ld:
            vert_angle = max(0.0, vert_base - 4)
            launch = swing_angle + vert_angle + power_adjust
            if launch > 15:
                vert_angle -= launch - 15
            outcome = "line"
        else:
            vert_angle = max(0.0, vert_base - 4)
            launch = swing_angle + vert_angle + power_adjust
            if launch <= 15:
                vert_angle += 16 - launch
            outcome = "fly"
        launch_angle = swing_angle + vert_angle + power_adjust
        self.last_batted_ball_type = outcome
        self.last_batted_ball_angles = (swing_angle, vert_angle)
        if self.last_batted_ball_type == "ground":
            self._add_stat(batter_state, "gb")
            pitcher_state.gb += 1
        elif self.last_batted_ball_type == "line":
            self._add_stat(batter_state, "ld")
            pitcher_state.ld += 1
        else:
            self._add_stat(batter_state, "fb")
            pitcher_state.fb += 1
        movement_factor = max(
            self.config.movement_factor_min,
            ((100 - pitcher.movement) / 120)
            * self.config.movement_impact_scale,
        )
        ch_rating = getattr(batter, "ch", 50)
        # Center around an average rating of 50 so only above-average
        # contact skills provide a positive boost.
        contact_factor = (
            self.config.contact_factor_base
            + (ch_rating - 50) / self.config.contact_factor_div
        )
        hit_prob = max(
            0.0,
            min(
                self.config.get("hitProbCap", 0.95),
                (
                    (bat_speed / 100.0)
                    * contact_quality
                    * contact_factor
                    * movement_factor
                )
                + self.config.hit_prob_base,
            ),
        )
        # Modify hit probability based on current defensive alignment.
        infield_pos = self.current_field_positions.get("infield", {})
        if (
            self.current_infield_situation in infield_pos
            and "normal" in infield_pos
            and infield_pos["normal"]
        ):
            def _avg_depth(pos: Dict[str, Tuple[float, float]]) -> float:
                return sum(d for d, _ in pos.values()) / len(pos)

            normal_depth = _avg_depth(infield_pos["normal"])
            cur_depth = _avg_depth(infield_pos[self.current_infield_situation])
            if normal_depth > 0:
                hit_prob *= cur_depth / normal_depth

        if self.rng.random() >= hit_prob:
            if is_third_strike:
                self._last_swing_strikeout = True
                self.logged_strikeouts += 1
                catcher_fs = self._get_fielder(defense, "C")
                if catcher_fs:
                    self._add_fielding_stat(catcher_fs, "po", position="C")
            return None, False

        out_prob = {
            "ground": self.config.get("groundOutProb", 0.0),
            "line": self.config.get("lineOutProb", 0.0),
            "fly": self.config.get("flyOutProb", 0.0),
        }[self.last_batted_ball_type]

        roll_dist = self.physics.ball_roll_distance(
            bat_speed,
            self.surface,
            altitude=self.altitude,
            temperature=self.temperature,
            wind_speed=self.wind_speed,
        )
        bounce_vert, bounce_horiz = self.physics.ball_bounce(
            bat_speed / 2.0,
            bat_speed / 2.0,
            surface=self.surface,
            wet=self.wet,
            temperature=self.temperature,
        )

        vx, vy, vz = self.physics.launch_vector(
            getattr(batter, "ph", 50),
            getattr(batter, "pl", 50),
            swing_angle,
            vert_angle,
            swing_type=swing_type,
        )
        x, y, hang_time = self.physics.landing_point(vx, vy, vz)
        landing_dist = math.hypot(x, y)
        angle = math.atan2(abs(y), abs(x))

        offense = self.away if defense is self.home else self.home
        if (
            self.current_outs < 2
            and offense.bases[0] is not None
            and offense.bases[1] is not None
            and landing_dist <= 160
            and vert_angle >= 50
        ):
            self.infield_fly = True
            self.debug_log.append("Infield fly rule applied")
            return 0, False

        fielders = {p.primary_position.upper(): p for p in defense.lineup}
        fielders["P"] = pitcher
        for pos, (fx, fy) in DEFAULT_POSITIONS.items():
            fielder = fielders.get(pos)
            if not fielder:
                continue
            sp = getattr(fielder, "sp", 50)
            fa = getattr(fielder, "fa", 50)
            distance = math.hypot(fx - x, fy - y)
            run_time = (
                distance / self.physics.player_speed(sp)
                + self.physics.reaction_delay(pos, fa)
            )
            action = self.fielding_ai.catch_action(
                hang_time,
                run_time,
                position=pos,
                distance=distance,
                dist_from_home=landing_dist,
            )
            if action == "no_attempt":
                continue
            prob = self.fielding_ai.catch_probability(pos, fa, hang_time, action)
            prob *= out_prob * (1 + self.config.get("ballInPlayOuts", 0))
            prob = min(prob, 1.0)
            if self.rng.random() < prob:
                caught, error = self.fielding_ai.resolve_throw(pos, fa, hang_time)
                if caught:
                    return 0, False
                fs = defense.fielding_stats.setdefault(
                    fielder.player_id, FieldingState(fielder)
                )
                self._add_fielding_stat(fs, "e")
                return 1, True

        total_dist = landing_dist + bounce_horiz + roll_dist
        wall = self.stadium.wall_distance(angle)
        if total_dist >= wall:
            return 4, False
        if total_dist >= self.stadium.triple_distance(angle):
            return 3, False
        if total_dist >= self.stadium.double_distance(angle):
            return 2, False
        return 1, False

    def _advance_runners(
        self,
        offense: TeamState,
        defense: TeamState,
        batter_state: BatterState,
        *,
        bases: int,
        error: bool = False,
    ) -> None:
        b = offense.bases
        bp = offense.base_pitchers
        new_bases: List[Optional[BatterState]] = [None, None, None]
        new_bp: List[Optional[PitcherState]] = [None, None, None]
        runs_scored = 0
        outs = 0
        aggression = float(self.config.get("baserunningAggression", 0.5))
        arm = getattr(defense.lineup[0], "arm", 0) if defense.lineup else 0

        if error:
            self._add_stat(batter_state, "roe")

        if bases == 1:
            runner_on_first_out = False
            force_runner_time: Optional[float] = None
            force_fielder_time: Optional[float] = None
            if b[2]:
                runner_time = 90 / self.physics.player_speed(b[2].player.sp)
                fielder_time = self.physics.reaction_delay("LF", 0) + self.physics.throw_time(arm, 90, "LF")
                if self.fielding_ai.should_tag_runner(fielder_time, runner_time):
                    outs += 1
                else:
                    self._score_runner(offense, defense, 2)
                    runs_scored += 1
            if b[1]:
                spd = self.physics.player_speed(b[1].player.sp)
                roll_dist = self.physics.ball_roll_distance(
                    spd,
                    self.surface,
                    altitude=self.altitude,
                    temperature=self.temperature,
                    wind_speed=self.wind_speed,
                )
                _, bounce_dist = self.physics.ball_bounce(
                    spd / 2.0,
                    spd / 2.0,
                    surface=self.surface,
                    wet=self.wet,
                    temperature=self.temperature,
                )
                attempt_home = roll_dist + bounce_dist >= 25 or self.rng.random() < aggression
                if attempt_home:
                    runner_time = 180 / spd
                    fielder_time = (
                        self.physics.reaction_delay("LF", 0)
                        + self.physics.throw_time(arm, 180, "LF")
                    )
                    if self.fielding_ai.should_tag_runner(fielder_time, runner_time):
                        outs += 1
                    else:
                        self._score_runner(offense, defense, 1)
                        runs_scored += 1
                else:
                    new_bases[2] = b[1]
                    new_bp[2] = bp[1]
            if b[0]:
                spd = self.physics.player_speed(b[0].player.sp)
                roll_dist = self.physics.ball_roll_distance(
                    spd,
                    self.surface,
                    altitude=self.altitude,
                    temperature=self.temperature,
                    wind_speed=self.wind_speed,
                )
                _, bounce_dist = self.physics.ball_bounce(
                    spd / 2.0,
                    spd / 2.0,
                    surface=self.surface,
                    wet=self.wet,
                    temperature=self.temperature,
                )
                attempt_third = roll_dist + bounce_dist >= 25 or self.rng.random() < aggression
                if attempt_third:
                    runner_time = 180 / spd
                    fielder_time = (
                        self.physics.reaction_delay("LF", 0)
                        + self.physics.throw_time(arm, 180, "LF")
                    )
                    if self.fielding_ai.should_tag_runner(fielder_time, runner_time):
                        outs += 1
                    else:
                        if new_bases[2] is None:
                            new_bases[2] = b[0]
                            new_bp[2] = bp[0]
                        else:
                            new_bases[1] = b[0]
                            new_bp[1] = bp[0]
                else:
                    runner_time = 90 / spd
                    fielder_time = (
                        self.physics.reaction_delay("SS", 0)
                        + self.physics.throw_time(arm, 90, "SS")
                    )
                    if self.fielding_ai.should_tag_runner(fielder_time, runner_time):
                        outs += 1
                        runner_on_first_out = True
                        force_runner_time = runner_time
                        force_fielder_time = fielder_time
                    else:
                        new_bases[1] = b[0]
                        new_bp[1] = bp[0]

            if runner_on_first_out:
                batter_time = 90 / self.physics.player_speed(batter_state.player.sp)
                relay_time = (
                    self.physics.reaction_delay("2B", 0)
                    + self.physics.throw_time(arm, 90, "2B")
                )
                dp_prob = self.config.get("doublePlayProb", 0)
                if force_runner_time and force_fielder_time:
                    margin = force_runner_time - force_fielder_time
                    if margin > 0:
                        dp_prob = min(1.0, dp_prob + margin * 0.05)
                time_margin = batter_time - relay_time
                if time_margin > 0:
                    dp_prob = min(1.0, dp_prob + time_margin * 0.05)
                if self.rng.random() < dp_prob:
                    outs += 1
                    self._add_stat(batter_state, "gidp")
                elif (
                    self.fielding_ai.should_relay_throw(relay_time, batter_time)
                    and self.fielding_ai.should_tag_runner(relay_time, batter_time)
                ):
                    outs += 1
                    self._add_stat(batter_state, "gidp")
                else:
                    new_bases[0] = batter_state
                    new_bp[0] = defense.current_pitcher_state
                    self._add_stat(batter_state, "fc")
            else:
                new_bases[0] = batter_state
                new_bp[0] = defense.current_pitcher_state

            offense.bases = new_bases
            offense.base_pitchers = new_bp
            if runs_scored and not error:
                self._add_stat(batter_state, "rbi", runs_scored)
            return outs

        for idx in range(2, -1, -1):
            runner = b[idx]
            if runner is None:
                continue
            target = idx + bases
            if target >= 3:
                self._score_runner(offense, defense, idx)
                runs_scored += 1
            else:
                new_bases[target] = runner
                new_bp[target] = bp[idx]

        offense.bases = new_bases
        offense.base_pitchers = new_bp

        if bases >= 4:
            offense.runs += 1
            self._add_stat(batter_state, "r")
            pitcher = defense.current_pitcher_state
            if pitcher is not None:
                pitcher.r += 1
                pitcher.er += 1
                pitcher.toast += self.config.get("pitchScoringRun", 0)
                pitcher.toast += self.config.get("pitchScoringER", 0)
            runs_scored += 1
        else:
            base_idx = bases - 1
            offense.bases[base_idx] = batter_state
            offense.base_pitchers[base_idx] = defense.current_pitcher_state

        if runs_scored and not error:
            self._add_stat(batter_state, "rbi", runs_scored)
        return outs

    def _advance_walk(
        self, offense: TeamState, defense: TeamState, batter_state: BatterState
    ) -> None:
        b = offense.bases
        bp = offense.base_pitchers
        new_bases: List[Optional[BatterState]] = [None, None, None]
        new_bp: List[Optional[PitcherState]] = [None, None, None]
        runs_scored = 0
        if b[2] and b[1] and b[0]:
            self._score_runner(offense, defense, 2)
            runs_scored += 1
        if b[1] and b[0]:
            new_bases[2] = b[1]
            new_bp[2] = bp[1]
        elif b[2]:
            new_bases[2] = b[2]
            new_bp[2] = bp[2]
        if b[0]:
            new_bases[1] = b[0]
            new_bp[1] = bp[0]
        new_bases[0] = batter_state
        new_bp[0] = defense.current_pitcher_state
        offense.bases = new_bases
        offense.base_pitchers = new_bp
        if runs_scored:
            self._add_stat(batter_state, "rbi", runs_scored)

    def _advance_passed_ball(
        self, offense: TeamState, defense: TeamState
    ) -> None:
        """Advance all runners one base on a passed ball."""

        b = offense.bases
        bp = offense.base_pitchers
        if b[2]:
            self._score_runner(offense, defense, 2)
        if b[1]:
            offense.bases[2] = b[1]
            offense.base_pitchers[2] = bp[1]
            offense.bases[1] = None
            offense.base_pitchers[1] = None
        if b[0]:
            offense.bases[1] = b[0]
            offense.base_pitchers[1] = bp[0]
            offense.bases[0] = None
            offense.base_pitchers[0] = None

    def _maybe_passed_ball(
        self,
        offense: TeamState,
        defense: TeamState,
        catcher_fs: Optional[FieldingState],
    ) -> bool:
        """Return ``True`` if a passed ball occurs."""

        if catcher_fs is None or not any(offense.bases):
            return False
        fa = catcher_fs.player.fa
        pb_chance = max(0.0, 0.01 - fa / 10000)
        if self.rng.random() < pb_chance:
            self._add_fielding_stat(catcher_fs, "pb")
            self._advance_passed_ball(offense, defense)
            return True
        return False

    def _maybe_catcher_interference(
        self,
        offense: TeamState,
        defense: TeamState,
        batter_state: BatterState,
        catcher_fs: Optional[FieldingState],
        pitcher_state: PitcherState,
        start_pitches: int,
    ) -> bool:
        """Return ``True`` if catcher's interference is called."""

        if catcher_fs is None:
            return False
        fa = catcher_fs.player.fa
        ci_chance = max(0.0, 0.001 - fa / 100000)
        if self.rng.random() < ci_chance:
            self._add_fielding_stat(catcher_fs, "ci")
            self._add_stat(batter_state, "ci")
            self._advance_walk(offense, defense, batter_state)
            self._add_stat(
                batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
            )
            return True
        return False

    # ------------------------------------------------------------------
    # Steal attempts
    # ------------------------------------------------------------------
    def _attempt_steal(
        self,
        offense: TeamState,
        defense: TeamState,
        pitcher: Pitcher,
        *,
        force: bool = False,
        batter: Player | None = None,
        balls: int = 0,
        strikes: int = 0,
        outs: int = 0,
        runner_on: int = 1,
        batter_ch: int = 50,
        pitcher_is_wild: bool = False,
        pitcher_in_windup: bool = False,
        run_diff: int = 0,
    ) -> Optional[bool]:
        base_idx = runner_on - 1
        if base_idx not in (0, 1):
            return None
        runner_state = offense.bases[base_idx]
        if not runner_state or runner_state.lead < 2:
            return None
        if runner_on == 2 and offense.bases[2] is not None:
            return None
        attempt = force
        if not attempt:
            if batter is not None:
                batter_ch = batter.ch
            chance = self.offense.calculate_steal_chance(
                balls=balls,
                strikes=strikes,
                runner_sp=runner_state.player.sp,
                pitcher_hold=pitcher.hold_runner,
                pitcher_is_left=pitcher.bats == "L",
                pitcher_is_wild=pitcher_is_wild,
                pitcher_in_windup=pitcher_in_windup,
                outs=outs,
                runner_on=runner_on,
                batter_ch=batter_ch,
                run_diff=run_diff,
            )
            attempt = self.rng.random() < chance
        if attempt:
            catcher_fs = self._get_fielder(defense, "C")
            if catcher_fs and self._maybe_passed_ball(offense, defense, catcher_fs):
                self._add_stat(runner_state, "sb")
                return True
            fa = catcher_fs.player.fa if catcher_fs else 0
            delay = self.physics.reaction_delay("C", fa)
            # Original logic assumes the tag play beats the runner; incorporate
            # arm strength by reducing the success probability for stronger
            # pitcher/catcher arms.
            self.fielding_ai.should_tag_runner(delay, 10)
            tag_pct = self.config.get("stealSuccessTagOutPct", 20) / 100.0
            catcher_arm = catcher_fs.player.arm if catcher_fs else 0
            arm_factor = (catcher_arm + pitcher.arm) / 200.0
            success_prob = tag_pct * (1 - arm_factor / 2)
            if self.rng.random() < success_prob:
                ps_runner = offense.base_pitchers[base_idx]
                offense.bases[base_idx] = None
                offense.base_pitchers[base_idx] = None
                offense.bases[base_idx + 1] = runner_state
                offense.base_pitchers[base_idx + 1] = ps_runner
                self._add_stat(runner_state, "sb")
                if catcher_fs:
                    self._add_fielding_stat(catcher_fs, "sba")
                return True
            offense.bases[base_idx] = None
            offense.base_pitchers[base_idx] = None
            self._add_stat(runner_state, "cs")
            if catcher_fs:
                self._add_fielding_stat(catcher_fs, "sba")
                self._add_fielding_stat(catcher_fs, "cs")
                self._add_fielding_stat(catcher_fs, "a")
            if runner_on == 1:
                tagger = self._get_fielder(defense, "2B") or self._get_fielder(defense, "SS")
            else:
                tagger = self._get_fielder(defense, "3B")
            if tagger:
                self._add_fielding_stat(
                    tagger,
                    "po",
                    position=getattr(tagger.player, "primary_position", None),
                )
            return False
        return None

    # ------------------------------------------------------------------
    # Pitching changes
    # ------------------------------------------------------------------

def generate_boxscore(home: TeamState, away: TeamState) -> Dict[str, Dict[str, object]]:
    """Return a simplified box score for ``home`` and ``away`` teams."""

    def team_section(team: TeamState) -> Dict[str, object]:
        batting = []
        for bs in team.lineup_stats.values():
            line = {
                "player": bs.player,
                "pa": bs.pa,
                "ab": bs.ab,
                "r": bs.r,
                "h": bs.h,
                "1b": bs.b1,
                "2b": bs.b2,
                "3b": bs.b3,
                "hr": bs.hr,
                "rbi": bs.rbi,
                "bb": bs.bb,
                "ibb": bs.ibb,
                "hbp": bs.hbp,
                "so": bs.so,
                "sh": bs.sh,
                "sf": bs.sf,
                "roe": bs.roe,
                "fc": bs.fc,
                "ci": bs.ci,
                "gidp": bs.gidp,
                "sb": bs.sb,
                "cs": bs.cs,
                "po": bs.po,
                "pocs": bs.pocs,
            }
            line.update(compute_batting_derived(bs))
            line.update(compute_batting_rates(bs))
            batting.append(line)
        pitching = []
        for ps in team.pitcher_stats.values():
            line = {
                "player": ps.player,
                "g": ps.g,
                "gs": ps.gs,
                "bf": ps.bf,
                "outs": ps.outs,
                "r": ps.r,
                "er": ps.er,
                "h": ps.h,
                "1b": ps.b1,
                "2b": ps.b2,
                "3b": ps.b3,
                "hr": ps.hr,
                "bb": ps.bb,
                "ibb": ps.ibb,
                "hbp": ps.hbp,
                "so": ps.so,
                "wp": ps.wp,
                "bk": ps.bk,
                "pk": ps.pk,
                "pocs": ps.pocs,
                "ir": ps.ir,
                "irs": ps.irs,
                "gf": ps.gf,
                "sv": ps.sv,
                "bs": ps.bs,
                "hld": ps.hld,
                "svo": ps.svo,
                "pitches": ps.pitches_thrown,
                "strikes": ps.strikes_thrown,
                "balls": ps.balls_thrown,
            }
            line.update(compute_pitching_derived(ps))
            line.update(compute_pitching_rates(ps))
            pitching.append(line)
        fielding = []
        for fs in team.fielding_stats.values():
            line = {
                "player": fs.player,
                "g": fs.g,
                "gs": fs.gs,
                "po": fs.po,
                "a": fs.a,
                "e": fs.e,
                "dp": fs.dp,
                "tp": fs.tp,
                "pk": fs.pk,
                "pb": fs.pb,
                "ci": fs.ci,
                "cs": fs.cs,
                "sba": fs.sba,
            }
            line.update(compute_fielding_derived(fs))
            line.update(compute_fielding_rates(fs))
            fielding.append(line)
        return {
            "score": team.runs,
            "batting": batting,
            "pitching": pitching,
            "fielding": fielding,
            "inning_runs": team.inning_runs,
        }

    return {"home": team_section(home), "away": team_section(away)}


# ---------------------------------------------------------------------------
# Box score HTML rendering / saving
# ---------------------------------------------------------------------------
from datetime import datetime
from pathlib import Path


def render_boxscore_html(
    box: Dict[str, Dict[str, object]],
    home_name: str = "Home",
    away_name: str = "Away",
    league: str = "League",
    home_abbr: str | None = None,
    away_abbr: str | None = None,
) -> str:
    """Render ``box`` using the ``espn_boxscore_template.html`` sample."""

    home_abbr = home_abbr or home_name
    away_abbr = away_abbr or away_name

    template_path = get_base_dir() / "samples" / "espn_boxscore_template.html"
    template = template_path.read_text(encoding="utf-8")

    repl: Dict[str, object] = {
        "league": league,
        "home.name": home_name,
        "away.name": away_name,
        "home.abbr": home_abbr,
        "away.abbr": away_abbr,
        "home.score": box["home"]["score"],
        "away.score": box["away"]["score"],
    }

    def totals(side: str) -> tuple[int, int, int]:
        hits = sum(e["h"] for e in box[side]["batting"])
        errors = sum(e["e"] for e in box[side]["fielding"])
        return box[side]["score"], hits, errors

    for side in ("home", "away"):
        r, h, e = totals(side)
        repl[f"totals.{side}.r"] = r
        repl[f"totals.{side}.h"] = h
        repl[f"totals.{side}.e"] = e

    for i in range(9):
        repl[f"linescore.home[{i}]"] = (
            box["home"]["inning_runs"][i] if i < len(box["home"]["inning_runs"]) else ""
        )
        repl[f"linescore.away[{i}]"] = (
            box["away"]["inning_runs"][i] if i < len(box["away"]["inning_runs"]) else ""
        )

    import re

    def replace_loop(var: str, key: str, entries: list[dict]) -> None:
        nonlocal template
        pattern = re.compile(rf"{{{{#for {var} in {key}}}}}(.*?){{{{/for}}}}", re.DOTALL)
        m = pattern.search(template)
        if not m:
            return
        block = m.group(1)
        rows: list[str] = []
        for entry in entries:
            row = block
            p = entry["player"]
            name = f"{p.first_name} {p.last_name}"
            if var == "batter":
                mapping = {
                    "name": name,
                    "pos": getattr(p, "position", ""),
                    "AB": entry.get("ab", 0),
                    "R": entry.get("r", 0),
                    "H": entry.get("h", 0),
                    "RBI": entry.get("rbi", 0),
                    "BB": entry.get("bb", 0),
                    "K": entry.get("so", 0),
                    "HR": entry.get("hr", 0),
                    "AVG": f"{entry.get('avg', 0):.3f}",
                    "OBP": f"{entry.get('obp', 0):.3f}",
                    "SLG": f"{entry.get('slg', 0):.3f}",
                }
            else:
                outs = entry.get("outs", 0)
                ip = f"{outs // 3}.{outs % 3}"
                mapping = {
                    "name": name,
                    "IP": ip,
                    "H": entry.get("h", 0),
                    "R": entry.get("r", 0),
                    "ER": entry.get("er", 0),
                    "BB": entry.get("bb", 0),
                    "K": entry.get("so", 0),
                    "HR": entry.get("hr", 0),
                    "PC-ST": f"{entry.get('pitches', 0)}-{entry.get('strikes', 0)}",
                    "ERA": f"{entry.get('era', 0):.2f}",
                }
            for k, v in mapping.items():
                row = row.replace(f"{{{{{var}.{k}}}}}", str(v))
            rows.append(row)
        template = pattern.sub("".join(rows), template)

    replace_loop("batter", "batting.home", box["home"]["batting"])
    replace_loop("batter", "batting.away", box["away"]["batting"])
    replace_loop("pitcher", "pitching.home", box["home"]["pitching"])
    replace_loop("pitcher", "pitching.away", box["away"]["pitching"])

    def batting_totals(side: str) -> tuple[int, int, int, int, int, int, int]:
        entries = box[side]["batting"]
        ab = sum(e["ab"] for e in entries)
        r = sum(e["r"] for e in entries)
        h = sum(e["h"] for e in entries)
        rbi = sum(e["rbi"] for e in entries)
        bb = sum(e["bb"] for e in entries)
        k = sum(e["so"] for e in entries)
        hr = sum(e["hr"] for e in entries)
        return ab, r, h, rbi, bb, k, hr

    for side in ("home", "away"):
        ab, r, h, rbi, bb, k, hr = batting_totals(side)
        repl[f"batting_totals.{side}.AB"] = ab
        repl[f"batting_totals.{side}.R"] = r
        repl[f"batting_totals.{side}.H"] = h
        repl[f"batting_totals.{side}.RBI"] = rbi
        repl[f"batting_totals.{side}.BB"] = bb
        repl[f"batting_totals.{side}.K"] = k
        repl[f"batting_totals.{side}.HR"] = hr
        repl[f"notes.{side}.batting"] = ""
        repl[f"notes.{side}.risp"] = ""
        repl[f"notes.{side}.fielding"] = ""

    for key, value in repl.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    # Remove any unreplaced placeholders to avoid leaking template tokens
    template = re.sub(r"{{[^{}]+}}", "", template)
    return template


def save_boxscore_html(game_type: str, html: str, game_id: str | None = None) -> str:
    """Persist ``html`` to the appropriate box score directory.

    Parameters
    ----------
    game_type:
        Either ``"exhibition"`` or ``"season"``.
    html:
        The HTML to write.
    game_id:
        Optional file name stem.  If not provided a timestamp is used.

    Returns
    -------
    str
        Full path of the written file.
    """

    base = get_base_dir() / "data" / "boxscores" / game_type
    base.mkdir(parents=True, exist_ok=True)
    if game_id is None:
        game_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = base / f"{game_id}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


__all__ = [
    "BatterState",
    "FieldingState",
    "TeamState",
    "GameSimulation",
    "generate_boxscore",
    "render_boxscore_html",
    "save_boxscore_html",
]
