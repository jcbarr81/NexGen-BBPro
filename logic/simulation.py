from __future__ import annotations

import random
from dataclasses import dataclass, field
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


@dataclass
class PitcherState:
    """Tracks state for a pitcher."""

    player: Pitcher
    pitches_thrown: int = 0
    walks: int = 0
    strikeouts: int = 0


@dataclass
class TeamState:
    """Mutable state for a team during a game."""

    lineup: List[Player]
    bench: List[Player]
    pitchers: List[Pitcher]
    lineup_stats: Dict[str, BatterState] = field(default_factory=dict)
    pitcher_stats: Dict[str, PitcherState] = field(default_factory=dict)
    batting_index: int = 0
    bases: List[Optional[BatterState]] = field(default_factory=lambda: [None, None, None])
    runs: int = 0
    inning_runs: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.pitchers:
            starter = self.pitchers[0]
            state = PitcherState(starter)
            self.pitcher_stats[starter.player_id] = state
            self.current_pitcher_state = state
        else:
            self.current_pitcher_state = None


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

    def _play_half(self, offense: TeamState, defense: TeamState) -> None:
        # Allow the defensive team to consider a late inning defensive swap
        self.subs.maybe_defensive_sub(defense, self.debug_log)

        start_runs = offense.runs
        outs = 0
        while outs < 3:
            outs += self.play_at_bat(offense, defense)
        offense.bases = [None, None, None]
        offense.inning_runs.append(offense.runs - start_runs)

    def play_at_bat(self, offense: TeamState, defense: TeamState) -> int:
        """Play a single at-bat.  Returns the number of outs recorded."""

        self.subs.maybe_change_pitcher(defense, self.debug_log)

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
        batter = self.subs.maybe_double_switch(
            offense, defense, batter_idx, self.debug_log
        )
        if batter is None:
            batter = self.subs.maybe_pinch_hit(offense, batter_idx, self.debug_log)
        offense.batting_index += 1

        batter_state = offense.lineup_stats.setdefault(
            batter.player_id, BatterState(batter)
        )
        pitcher_state = defense.current_pitcher_state
        if pitcher_state is None:
            raise RuntimeError("Defense has no available pitcher")

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
            pitcher_state.walks += 1
            self._advance_walk(offense, batter_state)
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
                    offense, pitcher_state.player, force=True
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
                runs_scored = 0
                if b[2]:
                    offense.runs += 1
                    self._add_stat(b[2], "r")
                    runs_scored += 1
                    b[2] = None
                if b[1]:
                    b[2] = b[1]
                    b[1] = None
                if b[0]:
                    b[1] = b[0]
                    b[0] = None
                self._add_stat(batter_state, "sh")
                if runs_scored:
                    self._add_stat(batter_state, "rbi", runs_scored)
                outs += 1
                return outs

        if offense.bases[2] and self.offense.maybe_suicide_squeeze(
            batter_ch=batter.ch,
            batter_ph=batter.ph,
            balls=balls,
            strikes=strikes,
            runner_on_third_sp=offense.bases[2].player.sp,
        ):
            self.debug_log.append("Suicide squeeze")
            offense.runs += 1
            runner = offense.bases[2]
            if runner:
                self._add_stat(runner, "r")
            offense.bases[2] = None
            self._add_stat(batter_state, "sh")
            self._add_stat(batter_state, "rbi")
            outs += 1
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
                    self._add_stat(batter_state, "ab")
                    self._add_stat(batter_state, "h")
                    self._add_stat(batter_state, "b1")
                    self._advance_runners(offense, batter_state)
                    steal_result = self._attempt_steal(
                        offense, pitcher_state.player, batter=batter
                    )
                    if steal_result is False:
                        outs += 1
                    return outs
                strikes += 1
            else:
                if dist <= 3:
                    strikes += 1
                else:
                    balls += 1

            if balls >= 4:
                self._add_stat(batter_state, "bb")
                if ibb:
                    self._add_stat(batter_state, "ibb")
                pitcher_state.walks += 1
                self._advance_walk(offense, batter_state)
                return outs
            if strikes >= 3:
                self._add_stat(batter_state, "ab")
                self._add_stat(batter_state, "so")
                pitcher_state.strikeouts += 1
                outs += 1
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

    def _advance_runners(self, team: TeamState, batter_state: BatterState) -> None:
        b = team.bases
        new_bases: List[Optional[BatterState]] = [None, None, None]
        runs_scored = 0

        # Runner on third always scores
        if b[2]:
            team.runs += 1
            self._add_stat(b[2], "r")
            runs_scored += 1

        # Runner on second may score depending on speed
        if b[1]:
            spd = self.physics.player_speed(b[1].player.sp)
            if spd >= 25:
                team.runs += 1
                self._add_stat(b[1], "r")
                runs_scored += 1
            else:
                new_bases[2] = b[1]

        # Runner on first may take two bases if fast enough
        if b[0]:
            spd = self.physics.player_speed(b[0].player.sp)
            if spd >= 25:
                if new_bases[2] is None:
                    new_bases[2] = b[0]
                else:
                    # Third base occupied, runner stops at second
                    new_bases[1] = b[0]
            else:
                new_bases[1] = b[0]

        # Batter to first
        new_bases[0] = batter_state
        team.bases = new_bases
        if runs_scored:
            self._add_stat(batter_state, "rbi", runs_scored)

    def _advance_walk(self, team: TeamState, batter_state: BatterState) -> None:
        b = team.bases
        runs_scored = 0
        if b[2] and b[1] and b[0]:
            team.runs += 1
            self._add_stat(b[2], "r")
            runs_scored += 1
        if b[1] and b[0]:
            b[2] = b[1]
        if b[0]:
            b[1] = b[0]
        b[0] = batter_state
        if runs_scored:
            self._add_stat(batter_state, "rbi", runs_scored)

    # ------------------------------------------------------------------
    # Steal attempts
    # ------------------------------------------------------------------
    def _attempt_steal(
        self,
        offense: TeamState,
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
            if self.rng.random() < success_prob:
                offense.bases[0] = None
                offense.bases[1] = runner_state
                self._add_stat(runner_state, "sb")
                return True
            offense.bases[0] = None
            self._add_stat(runner_state, "cs")
            return False
        return None

    # ------------------------------------------------------------------
    # Pitching changes
    # ------------------------------------------------------------------

def generate_boxscore(home: TeamState, away: TeamState) -> Dict[str, Dict[str, object]]:
    """Return a simplified box score for ``home`` and ``away`` teams."""

    def team_section(team: TeamState) -> Dict[str, object]:
        batting = [
            {
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
            for bs in team.lineup_stats.values()
        ]
        pitching = [
            {
                "player": ps.player,
                "pitches": ps.pitches_thrown,
                "bb": ps.walks,
                "so": ps.strikeouts,
            }
            for ps in team.pitcher_stats.values()
        ]
        return {
            "score": team.runs,
            "batting": batting,
            "pitching": pitching,
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
        return (
            f"<b>{name:<15}</b>{innings_str}   {box[key]['score']:>2}   {hits:>2}   0"
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
                    f"{p.first_name} {p.last_name}: {entry['pitches']} pitches, BB {entry['bb']}, SO {entry['so']}"
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
    "TeamState",
    "GameSimulation",
    "generate_boxscore",
    "render_boxscore_html",
    "save_boxscore_html",
]
