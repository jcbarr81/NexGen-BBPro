from __future__ import annotations

import random
from dataclasses import dataclass, field, fields
from typing import Dict, List, Optional

from models.player import Player
from models.pitcher import Pitcher
from logic.defensive_manager import DefensiveManager
from logic.offensive_manager import OffensiveManager
from logic.substitution_manager import SubstitutionManager
from logic.playbalance_config import PlayBalanceConfig
from logic.physics import Physics
from logic.pitcher_ai import PitcherAI
from logic.batter_ai import BatterAI
from .stats import (
    compute_batting_derived,
    compute_batting_rates,
    compute_pitching_derived,
    compute_pitching_rates,
    compute_fielding_derived,
    compute_fielding_rates,
)


@dataclass
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


@dataclass
class PitcherState:
    """Tracks state for a pitcher."""

    player: Pitcher
    g: int = 0  # Games pitched
    gs: int = 0  # Games started
    bf: int = 0  # Batters faced
    outs: int = 0  # Outs recorded
    r: int = 0  # Runs allowed
    er: int = 0  # Earned runs allowed
    h: int = 0  # Hits allowed
    b1: int = 0  # Singles allowed
    b2: int = 0  # Doubles allowed
    b3: int = 0  # Triples allowed
    hr: int = 0  # Home runs allowed
    bb: int = 0  # Walks issued
    ibb: int = 0  # Intentional walks issued
    hbp: int = 0  # Hit batters
    so: int = 0  # Strikeouts
    wp: int = 0  # Wild pitches
    bk: int = 0  # Balks
    pk: int = 0  # Pickoffs
    ir: int = 0  # Inherited runners
    irs: int = 0  # Inherited runners scored
    gf: int = 0  # Games finished
    sv: int = 0  # Saves
    bs: int = 0  # Blown saves
    hld: int = 0  # Holds
    svo: int = 0  # Save opportunities
    pitches_thrown: int = 0  # Total pitches
    strikes_thrown: int = 0  # Strikes thrown
    balls_thrown: int = 0  # Balls thrown
    first_pitch_strikes: int = 0  # First-pitch strikes
    zone_pitches: int = 0  # Pitches in the strike zone
    zone_swings: int = 0  # Swings at pitches in the zone
    zone_contacts: int = 0  # Contact on zone swings
    o_zone_swings: int = 0  # Swings at pitches outside the zone
    o_zone_contacts: int = 0  # Contact on outside-zone swings
    in_save_situation: bool = False  # Internal flag tracking save opp

    # Backwards compatibility accessors
    @property
    def walks(self) -> int:  # pragma: no cover - simple alias
        return self.bb

    @walks.setter
    def walks(self, value: int) -> None:  # pragma: no cover - simple alias
        self.bb = value

    @property
    def strikeouts(self) -> int:  # pragma: no cover - simple alias
        return self.so

    @strikeouts.setter
    def strikeouts(self, value: int) -> None:  # pragma: no cover - simple alias
        self.so = value


@dataclass
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


@dataclass
class TeamState:
    """Mutable state for a team during a game."""

    lineup: List[Player]
    bench: List[Player]
    pitchers: List[Pitcher]
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

    def __post_init__(self) -> None:
        if self.pitchers:
            starter = self.pitchers[0]
            state = PitcherState(starter)
            self.pitcher_stats[starter.player_id] = state
            self.current_pitcher_state = state
            state.g += 1
            state.gs += 1
            fs = self.fielding_stats.setdefault(starter.player_id, FieldingState(starter))
            fs.g += 1
            fs.gs += 1
        else:
            self.current_pitcher_state = None
        for p in self.lineup:
            fs = self.fielding_stats.setdefault(p.player_id, FieldingState(p))
            fs.g += 1
            fs.gs += 1


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
        self.debug_log: List[str] = []

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

    def _add_fielding_stat(self, state: FieldingState, attr: str, amount: int = 1) -> None:
        """Increment ``attr`` on ``state`` and season totals."""

        setattr(state, attr, getattr(state, attr) + amount)
        season = getattr(state.player, "season_stats", None)
        if season is None:
            season = {}
            state.player.season_stats = season
        season[attr] = season.get(attr, 0) + amount

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
        pitcher_for_runner = offense.base_pitchers[base_idx]
        if pitcher_for_runner is not None:
            pitcher_for_runner.r += 1
            pitcher_for_runner.er += 1
            current = defense.current_pitcher_state
            if current is not None and current is not pitcher_for_runner:
                current.irs += 1
        offense.bases[base_idx] = None
        offense.base_pitchers[base_idx] = None

    # ------------------------------------------------------------------
    # Core loop helpers
    # ------------------------------------------------------------------
    def simulate_game(self, innings: int = 9) -> None:
        """Simulate ``innings`` innings.

        Only very small parts of a real baseball game are modelled – enough to
        exercise decision making paths for the tests.
        """

        for _ in range(innings):
            self._play_half(self.away, self.home)  # Top half
            self._play_half(self.home, self.away)  # Bottom half

        # Finalize pitching stats for pitchers who finished the game
        self._on_pitcher_exit(self.home.current_pitcher_state, self.away, self.home, game_finished=True)
        self._on_pitcher_exit(self.away.current_pitcher_state, self.home, self.away, game_finished=True)

        for team in (self.home, self.away):
            for bs in team.lineup_stats.values():
                season = getattr(bs.player, "season_stats", {})
                season_state = BatterState(bs.player)
                for f in fields(BatterState):
                    if f.name == "player":
                        continue
                    setattr(season_state, f.name, season.get(f.name, 0))
                season.update(compute_batting_derived(season_state))
                season.update(compute_batting_rates(season_state))
                bs.player.season_stats = season

            for ps in team.pitcher_stats.values():
                season = getattr(ps.player, "season_stats", {})
                for f in fields(PitcherState):
                    if f.name in {"player", "in_save_situation"}:
                        continue
                    season[f.name] = season.get(f.name, 0) + getattr(ps, f.name)
                season_state = PitcherState(ps.player)
                for f in fields(PitcherState):
                    if f.name in {"player", "in_save_situation"}:
                        continue
                    setattr(season_state, f.name, season.get(f.name, 0))
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

    def _play_half(self, offense: TeamState, defense: TeamState) -> None:
        # Allow the defensive team to consider a late inning defensive swap
        self.subs.maybe_defensive_sub(defense, self.debug_log)

        start_runs = offense.runs
        outs = 0
        while outs < 3:
            outs += self.play_at_bat(offense, defense)
        for runner in offense.bases:
            if runner is not None:
                self._add_stat(runner, "lob")
        offense.bases = [None, None, None]
        offense.base_pitchers = [None, None, None]
        offense.inning_runs.append(offense.runs - start_runs)

    def play_at_bat(self, offense: TeamState, defense: TeamState) -> int:
        """Play a single at-bat.  Returns the number of outs recorded."""
        old_pitcher = defense.current_pitcher_state
        changed = self.subs.maybe_change_pitcher(defense, self.debug_log)
        if changed:
            self._on_pitcher_exit(old_pitcher, offense, defense)
            self._on_pitcher_enter(offense, defense)

        # Check if any existing runner should be replaced with a pinch runner
        self.subs.maybe_pinch_run(offense, log=self.debug_log)

        # Defensive decisions prior to the at-bat.  These mostly log the
        # outcome for manual inspection in the exhibition dialog.  The
        # simplified simulation does not yet modify gameplay based on them.
        runner = offense.bases[0].player if offense.bases[0] else None
        if self.defense.maybe_charge_bunt():
            self.debug_log.append("Defense charges bunt")
        if runner and self.defense.maybe_hold_runner(runner.sp):
            self.debug_log.append("Defense holds runner")
            if self.defense.maybe_pickoff():
                self.debug_log.append("Pickoff attempt")
            if self.defense.maybe_pitch_out():
                self.debug_log.append("Pitch out")
        pitch_around, ibb = self.defense.maybe_pitch_around()
        if ibb:
            self.debug_log.append("Intentional walk issued")
        elif pitch_around:
            self.debug_log.append("Pitch around")

        batter_idx = offense.batting_index % len(offense.lineup)
        old_pitcher = defense.current_pitcher_state
        batter = self.subs.maybe_double_switch(
            offense, defense, batter_idx, self.debug_log
        )
        if batter is not None:
            self._on_pitcher_exit(old_pitcher, offense, defense)
            self._on_pitcher_enter(offense, defense)
        else:
            batter = self.subs.maybe_pinch_hit(offense, batter_idx, self.debug_log)
        offense.batting_index += 1

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

        if ibb:
            self._add_stat(batter_state, "bb")
            self._add_stat(batter_state, "ibb")
            pitcher_state.bb += 1
            pitcher_state.ibb += 1
            self._advance_walk(offense, defense, batter_state)
            self._add_stat(
                batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
            )
            pitcher_state.outs += outs
            return outs

        runner_state = offense.bases[0]
        inning = len(offense.inning_runs) + 1
        run_diff = offense.runs - defense.runs

        if runner_state:
            if self.offense.maybe_hit_and_run(
                runner_sp=runner_state.player.sp,
                batter_ch=batter.ch,
                batter_ph=batter.ph,
            ):
                self.debug_log.append("Hit and run")
                steal_result = self._attempt_steal(
                    offense, defense, pitcher_state.player, force=True
                )
                if steal_result is False:
                    outs += 1
            elif self.offense.maybe_sacrifice_bunt(
                batter_is_pitcher=batter.primary_position == "P",
                batter_ch=batter.ch,
                batter_ph=batter.ph,
                outs=outs,
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
                return outs

        if offense.bases[2] and self.offense.maybe_suicide_squeeze(
            batter_ch=batter.ch,
            batter_ph=batter.ph,
            balls=balls,
            strikes=strikes,
            runner_on_third_sp=offense.bases[2].player.sp,
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
            return outs

        while True:
            pitcher_state.pitches_thrown += 1
            pitch_type, _ = self.pitcher_ai.select_pitch(
                pitcher_state.player, balls=balls, strikes=strikes
            )
            loc_r = self.rng.random()
            dist = 0 if loc_r < 0.5 else 5
            dec_r = self.rng.random()
            swing, contact = self.batter_ai.decide_swing(
                batter,
                pitcher_state.player,
                pitch_type=pitch_type,
                balls=balls,
                strikes=strikes,
                dist=dist,
                random_value=dec_r,
            )

            if swing:
                if self._swing_result(
                    batter, pitcher_state.player, rand=dec_r, contact_quality=contact
                ):
                    pitcher_state.strikes_thrown += 1
                    pitcher_state.h += 1
                    pitcher_state.b1 += 1
                    self._add_stat(batter_state, "ab")
                    self._add_stat(batter_state, "h")
                    self._add_stat(batter_state, "b1")
                    self._advance_runners(offense, defense, batter_state)
                    steal_result = self._attempt_steal(
                        offense, defense, pitcher_state.player, batter=batter
                    )
                    if steal_result is False:
                        outs += 1
                    self._add_stat(
                        batter_state,
                        "pitches",
                        pitcher_state.pitches_thrown - start_pitches,
                    )
                    pitcher_state.outs += outs
                    return outs
                strikes += 1
                pitcher_state.strikes_thrown += 1
            else:
                if dist <= 3:
                    strikes += 1
                    pitcher_state.strikes_thrown += 1
                else:
                    balls += 1
                    pitcher_state.balls_thrown += 1

            if balls >= 4:
                self._add_stat(batter_state, "bb")
                pitcher_state.bb += 1
                self._advance_walk(offense, defense, batter_state)
                self._add_stat(
                    batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
                )
                pitcher_state.outs += outs
                return outs
            if strikes >= 3:
                self._add_stat(batter_state, "ab")
                self._add_stat(batter_state, "so")
                pitcher_state.so += 1
                outs += 1
                catcher_fs = self._get_fielder(defense, "C")
                if catcher_fs:
                    self._add_fielding_stat(catcher_fs, "po")
                p_fs = defense.fielding_stats.get(pitcher_state.player.player_id)
                if p_fs:
                    self._add_fielding_stat(p_fs, "a")
                self._add_stat(
                    batter_state, "pitches", pitcher_state.pitches_thrown - start_pitches
                )
                pitcher_state.outs += outs
                return outs


    # ------------------------------------------------------------------
    # Pinch hitting
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Swing outcome
    # ------------------------------------------------------------------
    def _swing_result(
        self,
        batter: Player,
        pitcher: Pitcher,
        *,
        rand: float,
        contact_quality: float = 1.0,
    ) -> bool:
        bat_speed = self.physics.bat_speed(batter.ph)
        # The angle is calculated for completeness even though the simplified
        # simulation does not yet use it for the outcome.
        self.physics.swing_angle(batter.gf)
        hit_prob = max(0.0, min(0.95, (bat_speed / 100.0) * contact_quality))
        return rand < hit_prob

    def _advance_runners(
        self, offense: TeamState, defense: TeamState, batter_state: BatterState
    ) -> None:
        b = offense.bases
        bp = offense.base_pitchers
        new_bases: List[Optional[BatterState]] = [None, None, None]
        new_bp: List[Optional[PitcherState]] = [None, None, None]
        runs_scored = 0

        if b[2]:
            self._score_runner(offense, defense, 2)
            runs_scored += 1
        if b[1]:
            spd = self.physics.player_speed(b[1].player.sp)
            if spd >= 25:
                self._score_runner(offense, defense, 1)
                runs_scored += 1
            else:
                new_bases[2] = b[1]
                new_bp[2] = bp[1]
        if b[0]:
            spd = self.physics.player_speed(b[0].player.sp)
            if spd >= 25:
                if new_bases[2] is None:
                    new_bases[2] = b[0]
                    new_bp[2] = bp[0]
                else:
                    new_bases[1] = b[0]
                    new_bp[1] = bp[0]
            else:
                new_bases[1] = b[0]
                new_bp[1] = bp[0]

        new_bases[0] = batter_state
        new_bp[0] = defense.current_pitcher_state
        offense.bases = new_bases
        offense.base_pitchers = new_bp
        if runs_scored:
            self._add_stat(batter_state, "rbi", runs_scored)

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
    ) -> Optional[bool]:
        runner_state = offense.bases[0]
        if not runner_state:
            return None
        attempt = force
        if not attempt:
            batter_ch = batter.ch if batter else 50
            chance = self.offense.calculate_steal_chance(
                runner_sp=runner_state.player.sp,
                pitcher_hold=pitcher.hold_runner,
                pitcher_is_left=pitcher.bats == "L",
                batter_ch=batter_ch,
            )
            attempt = self.rng.random() < chance
        if attempt:
            success_prob = 0.7
            catcher_fs = self._get_fielder(defense, "C")
            if self.rng.random() < success_prob:
                ps_runner = offense.base_pitchers[0]
                offense.bases[0] = None
                offense.base_pitchers[0] = None
                offense.bases[1] = runner_state
                offense.base_pitchers[1] = ps_runner
                self._add_stat(runner_state, "sb")
                if catcher_fs:
                    self._add_fielding_stat(catcher_fs, "sba")
                return True
            offense.bases[0] = None
            offense.base_pitchers[0] = None
            self._add_stat(runner_state, "cs")
            if catcher_fs:
                self._add_fielding_stat(catcher_fs, "sba")
                self._add_fielding_stat(catcher_fs, "cs")
                self._add_fielding_stat(catcher_fs, "a")
            tagger = self._get_fielder(defense, "2B") or self._get_fielder(defense, "SS")
            if tagger:
                self._add_fielding_stat(tagger, "po")
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
) -> str:
    """Return a very small HTML representation of ``box``.

    The goal is not to be feature complete but to provide an easily testable
    HTML output that mirrors the structure of ``samples/BoxScoreSample.html``.
    """

    def team_line(key: str, name: str) -> str:
        innings = box[key]["inning_runs"]
        innings_str = "".join(f"{r:>3}" for r in innings)
        if len(innings) < 9:
            innings_str += "".join("   " for _ in range(9 - len(innings)))
        hits = sum(entry["h"] for entry in box[key]["batting"])
        errors = sum(entry["e"] for entry in box[key]["fielding"])
        return (
            f"<b>{name:<15}</b>{innings_str}   {box[key]['score']:>2}   {hits:>2}   {errors:>2}"
        )

    lines = ["<html><body><pre>"]
    lines.append("<b>                  1  2  3   4  5  6   7  8  9         R   H   E</b>")
    lines.append(team_line("away", away_name))
    lines.append(team_line("home", home_name))
    lines.append("</pre><hr><pre>")

    def team_section(key: str, name: str) -> None:
        lines.append(f"<b>{name} Batting</b>")
        for entry in box[key]["batting"]:
            p = entry["player"]
            lines.append(
                f"{p.first_name} {p.last_name}: {entry['h']}-{entry['ab']}, BB {entry['bb']}, SO {entry['so']}, SB {entry['sb']}"
            )
        if box[key]["pitching"]:
            lines.append("")
            lines.append(f"<b>{name} Pitching</b>")
            for entry in box[key]["pitching"]:
                p = entry["player"]
                lines.append(
                    f"{p.first_name} {p.last_name}: BF {entry['bf']}, R {entry['r']}, ER {entry['er']}, H {entry['h']}, BB {entry['bb']}, SO {entry['so']}, P {entry['pitches']}, S {entry['strikes']}"
                )
        if box[key]["fielding"]:
            lines.append("")
            lines.append(f"<b>{name} Fielding</b>")
            for entry in box[key]["fielding"]:
                p = entry["player"]
                lines.append(
                    f"{p.first_name} {p.last_name}: PO {entry['po']}, A {entry['a']}, E {entry['e']}"
                )
        lines.append("")

    team_section("away", away_name)
    team_section("home", home_name)
    lines.append("</pre></body></html>")
    return "\n".join(lines)


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

    base = Path(__file__).resolve().parent.parent / "data" / "boxscores" / game_type
    base.mkdir(parents=True, exist_ok=True)
    if game_id is None:
        game_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = base / f"{game_id}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


__all__ = [
    "BatterState",
    "PitcherState",
    "FieldingState",
    "TeamState",
    "GameSimulation",
    "generate_boxscore",
    "render_boxscore_html",
    "save_boxscore_html",
]
