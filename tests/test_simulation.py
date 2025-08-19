import random

from logic.simulation import (
    BatterState,
    GameSimulation,
    TeamState,
    generate_boxscore,
)
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import load_config, make_cfg


class MockRandom(random.Random):
    """Deterministic random generator using a predefined sequence."""

    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def random(self):  # type: ignore[override]
        if self.values:
            return self.values.pop(0)
        return 0.0

    def randint(self, a, b):  # type: ignore[override]
        # ``PitcherAI`` uses ``randint`` for pitch variation.  Returning the
        # lower bound keeps behaviour deterministic without consuming the
        # predefined sequence.
        return a


def make_player(
    pid: str, ph: int = 50, sp: int = 50, ch: int = 50, gf: int = 50
) -> Player:
    return Player(
        player_id=pid,
        first_name="F" + pid,
        last_name="L" + pid,
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="1B",
        other_positions=[],
        gf=gf,
        ch=ch,
        ph=ph,
        sp=sp,
        pl=0,
        vl=0,
        sc=0,
        fa=0,
        arm=0,
    )


def make_pitcher(
    pid: str,
    endurance: int = 100,
    hold_runner: int = 50,
    role: str = "SP",
    control: int = 50,
    movement: int = 50,
) -> Pitcher:
    return Pitcher(
        player_id=pid,
        first_name="PF" + pid,
        last_name="PL" + pid,
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=50,
        endurance=endurance,
        control=control,
        movement=movement,
        hold_runner=hold_runner,
        fb=50,
        cu=0,
        cb=0,
        sl=0,
        si=0,
        scb=0,
        kn=0,
        arm=50,
        fa=50,
        role=role,
    )
def test_pinch_hitter_used():
    cfg = load_config()
    bench = make_player("bench", ph=80)
    starter = make_player("start", ph=10)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[starter], bench=[bench], pitchers=[make_pitcher("ap")])
    rng = MockRandom([0.0, 0.0, 0.0, 1.0])  # pinch, pitch strike, swing(hit), steal attempt none
    sim = GameSimulation(home, away, cfg, rng)
    sim.play_at_bat(away, home)
    assert away.lineup[0].player_id == "bench"
    stats = away.lineup_stats["bench"]
    assert stats.ab == 1


def test_pinch_hitter_not_used():
    cfg = load_config()
    bench = make_player("bench", ph=10)
    starter = make_player("start", ph=80)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[starter], bench=[bench], pitchers=[make_pitcher("ap")])
    rng = MockRandom([0.9] + [0.9, 0.9] * 4)  # no pinch, four balls -> walk
    sim = GameSimulation(home, away, cfg, rng)
    sim.play_at_bat(away, home)
    assert away.lineup[0].player_id == "start"
    stats = away.lineup_stats["start"]
    assert stats.bb == 1


def test_pinch_hit_need_hit_used():
    cfg = make_cfg(phForHitBase=100)
    bench = make_player("bench", ph=80, ch=80)
    starter = make_player("start", ph=10, ch=10)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[starter], bench=[bench], pitchers=[make_pitcher("ap")])
    home.runs = 1
    away.runs = 0
    rng = MockRandom([0.0, 0.0, 0.0, 0.0, 1.0])
    sim = GameSimulation(home, away, cfg, rng)
    sim.play_at_bat(away, home)
    assert away.lineup[0].player_id == "bench"
    stats = away.lineup_stats["bench"]
    assert stats.ab == 1


def test_pinch_hit_need_run_used():
    cfg = make_cfg(phForRunBase=100)
    bench = make_player("bench", ph=80, ch=80)
    starter = make_player("start", ph=10, ch=10)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[starter], bench=[bench], pitchers=[make_pitcher("ap")])
    home.runs = 1
    away.runs = 0
    rng = MockRandom([0.0, 0.0, 0.0, 1.0])
    sim = GameSimulation(home, away, cfg, rng)
    sim.play_at_bat(away, home)
    assert away.lineup[0].player_id == "bench"
    stats = away.lineup_stats["bench"]
    assert stats.ab == 1


def test_steal_attempt_success():
    cfg = load_config()
    cfg.values.update({"holdChanceAdjust": 0})
    runner = make_player("run", sp=90)
    batter = make_player("bat", ph=80)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[0] = runner_state
    rng = MockRandom([0.0, 0.0, 0.0, 0.0])
    sim = GameSimulation(home, away, cfg, rng)
    outs = sim.play_at_bat(away, home)
    assert outs == 0
    stats = away.lineup_stats["run"]
    assert stats.sb == 1
    assert away.bases[2] is stats


def test_steal_attempt_failure():
    cfg = load_config()
    runner = make_player("run", sp=80)
    batter = make_player("bat", ph=80, sp=90)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[0] = runner_state
    cfg.values.update({"pitchOutChanceBase": 0, "holdChanceAdjust": 0})
    # hnr success ->0.0, steal failure ->0.9, pitch strike ->0.0,
    # swing hit ->0.0, post-hit steal attempt fails ->1.0
    rng = MockRandom([0.0, 0.9, 0.0, 0.0, 1.0])
    sim = GameSimulation(home, away, cfg, rng)
    outs = sim.play_at_bat(away, home)
    assert outs == 1
    assert away.bases[0] is not None


def test_catcher_reaction_delay_affects_steal():
    cfg = make_cfg(
        generalSlop=0,
        tagTimeSlop=0,
        delayBaseCatcher=12,
        delayFAPctCatcher=-4,
    )
    runner = make_player("run", sp=80)

    def make_catcher(pid: str, fa: int) -> Player:
        return Player(
            player_id=pid,
            first_name="F" + pid,
            last_name="L" + pid,
            birthdate="2000-01-01",
            height=72,
            weight=180,
            bats="R",
            primary_position="C",
            other_positions=[],
            gf=50,
            ch=0,
            ph=0,
            sp=0,
            pl=0,
            vl=0,
            sc=0,
            fa=fa,
            arm=0,
        )

    slow_def = TeamState(lineup=[make_catcher("cs", 0)], bench=[], pitchers=[make_pitcher("hp")])
    fast_def = TeamState(lineup=[make_catcher("cf", 100)], bench=[], pitchers=[make_pitcher("hp")])

    offense1 = TeamState(lineup=[runner], bench=[], pitchers=[make_pitcher("ap")])
    rstate1 = BatterState(runner)
    rstate1.lead = 2
    offense1.lineup_stats[runner.player_id] = rstate1
    offense1.bases[0] = rstate1
    sim1 = GameSimulation(slow_def, offense1, cfg, MockRandom([0.5]))
    res1 = sim1._attempt_steal(offense1, slow_def, slow_def.pitchers[0], force=True)
    assert res1 is True

    offense2 = TeamState(lineup=[runner], bench=[], pitchers=[make_pitcher("ap")])
    rstate2 = BatterState(runner)
    rstate2.lead = 2
    offense2.lineup_stats[runner.player_id] = rstate2
    offense2.bases[0] = rstate2
    sim2 = GameSimulation(fast_def, offense2, cfg, MockRandom([0.5]))
    res2 = sim2._attempt_steal(offense2, fast_def, fast_def.pitchers[0], force=True)
    assert res2 is False


def test_steal_count_and_situational_modifiers():
    cfg = make_cfg(
        offManStealChancePct=100,
        stealChance10Count=30,
        stealChanceOnFirst01OutHighCHThresh=70,
        stealChanceOnFirst01OutHighCHAdjust=20,
        stealChanceWayBehindThresh=-2,
        stealChanceWayBehindAdjust=25,
    )
    runner = make_player("run", sp=80)
    batter = make_player("bat", ch=80)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    runner_state.lead = 2
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[0] = runner_state
    sim = GameSimulation(home, away, cfg, MockRandom([0.0, 0.0]))
    res = sim._attempt_steal(
        away,
        home,
        home.current_pitcher_state.player,
        balls=1,
        strikes=0,
        outs=1,
        runner_on=1,
        batter_ch=80,
        pitcher_is_wild=False,
        pitcher_in_windup=False,
        run_diff=-3,
    )
    assert res is True

    runner2 = make_player("run2", sp=80)
    offense2 = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state2 = BatterState(runner2)
    offense2.lineup_stats[runner2.player_id] = runner_state2
    offense2.bases[0] = runner_state2
    sim2 = GameSimulation(home, offense2, cfg, MockRandom([0.0]))
    runner_state2.lead = 0
    res2 = sim2._attempt_steal(
        offense2,
        home,
        home.current_pitcher_state.player,
        force=True,
        runner_on=1,
    )
    assert res2 is None


def test_second_base_steal_attempt_success():
    cfg = load_config()
    runner = make_player("run", sp=80)
    batter = make_player("bat")
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    runner_state.lead = 2
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[1] = runner_state
    sim = GameSimulation(home, away, cfg, MockRandom([0.0]))
    res = sim._attempt_steal(
        away,
        home,
        home.current_pitcher_state.player,
        force=True,
        runner_on=2,
    )
    assert res is True
    assert away.bases[2] is runner_state
    assert runner_state.sb == 1


def test_pickoff_attempt_scares_runner():
    cfg = make_cfg(
        holdChanceBase=100,
        holdChanceMinRunnerSpeed=0,
        holdChanceAdjust=0,
        pickoffChanceBase=100,
        longLeadSpeed=60,
        pickoffScareSpeed=60,
    )
    runner = make_player("run", sp=60)
    offense = TeamState(lineup=[runner], bench=[], pitchers=[make_pitcher("op")])
    defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[make_pitcher("dp")])
    rstate = BatterState(runner)
    offense.lineup_stats[runner.player_id] = rstate
    offense.bases[0] = rstate
    sim = GameSimulation(defense, offense, cfg, MockRandom([0.0, 0.0]))
    sim._set_runner_leads(offense)
    assert rstate.lead == 2
    sim._maybe_pickoff(rstate, steal_chance=0)
    assert rstate.lead == 0

def test_hit_and_run_count_adjust():
    cfg = make_cfg(
        offManHNRChancePct=100,
        hnrChanceBase=0,
        hnrChance3BallsAdjust=100,
        pitchOutChanceBase=0,
        pitchOutChanceStealThresh=100,
        pitchOutChanceHitRunThresh=100,
        sacChanceBase=0,
    )
    runner = make_player("run")
    batter = make_player("bat")
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[0] = runner_state
    rng_vals = [
        0.9,
        0.9,
        0.9,
        0.9,
        0.9,
        0.9,
        0.0,
        0.0,
        0.9,
        0.0,
        0.9,
        0.0,
        0.9,
    ]
    sim = GameSimulation(home, away, cfg, MockRandom(rng_vals))
    sim.play_at_bat(away, home)
    assert any("Hit and run" in ev for ev in sim.debug_log)
    assert runner_state.sb == 1


def test_pitch_out_count_adjust():
    cfg = make_cfg(
        offManHNRChancePct=100,
        hnrChanceBase=0,
        hnrChance3BallsAdjust=60,
        pitchOutChanceBase=100,
        pitchOutChanceHitRunThresh=50,
        pitchOutChanceStealThresh=100,
        holdChanceBase=100,
        holdChanceMinRunnerSpeed=0,
        sacChanceBase=0,
    )
    runner = make_player("run")
    batter = make_player("bat")
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[0] = runner_state
    rng_vals = [
        0.9,
        0.9,
        0.9,
        0.9,
        0.9,
        0.9,
        0.9,
        0.0,
        0.9,
        0.9,
        0.0,
        0.9,
        0.9,
        0.0,
        0.9,
    ]
    sim = GameSimulation(home, away, cfg, MockRandom(rng_vals))
    sim.play_at_bat(away, home)
    assert any("Pitch out" in ev for ev in sim.debug_log)
    assert all("Hit and run" not in ev for ev in sim.debug_log)


def test_pitcher_change_when_tired():
    cfg = load_config()
    home = TeamState(
        lineup=[make_player("h1")],
        bench=[],
        pitchers=[make_pitcher("start", endurance=5), make_pitcher("relief")],
    )
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    rng = MockRandom([0.0, 0.0, 1.0])  # pitch strike, swing hit, no steal attempt
    sim = GameSimulation(home, away, cfg, rng)
    sim.play_at_bat(away, home)
    assert home.current_pitcher_state.player.player_id == "relief"


def test_pitcher_not_changed():
    cfg = load_config()
    home = TeamState(
        lineup=[make_player("h1")],
        bench=[],
        pitchers=[make_pitcher("start", endurance=30), make_pitcher("relief")],
    )
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    rng = MockRandom([0.0, 0.0, 1.0])  # pitch strike, swing hit, no steal
    sim = GameSimulation(home, away, cfg, rng)
    original_state = home.current_pitcher_state
    sim.play_at_bat(away, home)
    assert home.current_pitcher_state is original_state
    assert home.current_pitcher_state.player.player_id == "start"


def test_starter_replaced_when_toast():
    cfg = make_cfg(
        starterToastThreshInn1=0,
        starterToastThreshPerInn=0,
        pitchScoringHit=-2,
        pitcherTiredThresh=0,
        pitcherExhaustedThresh=0,
    )
    home = TeamState(
        lineup=[make_player("h1")],
        bench=[],
        pitchers=[make_pitcher("start"), make_pitcher("relief", role="RP")],
    )
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    rng = MockRandom([0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0])
    sim = GameSimulation(home, away, cfg, rng)
    sim.play_at_bat(away, home)
    assert home.current_pitcher_state.player.player_id == "start"
    assert home.warming_reliever
    sim.play_at_bat(away, home)
    assert home.current_pitcher_state.player.player_id == "relief"


def test_run_tracking_and_boxscore():
    cfg = load_config()
    runner = make_player("run")
    batter = make_player("bat", ph=80)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[2] = runner_state

    sim = GameSimulation(home, away, cfg, MockRandom([0.0, 0.0, 0.0, 0.9]))
    outs = sim.play_at_bat(away, home)  # run scores, runner thrown out
    strike_seq = [0.0, 0.9, 0.0, 0.9, 0.0, 0.9]
    sim = GameSimulation(home, away, cfg, MockRandom(strike_seq))
    outs += sim.play_at_bat(away, home)  # strikeout
    sim = GameSimulation(home, away, cfg, MockRandom(strike_seq))
    outs += sim.play_at_bat(away, home)  # strikeout
    away.bases = [None, None, None]
    away.inning_runs.append(away.runs)
    assert outs == 2
    assert away.runs == 1
    assert away.inning_runs == [1]
    runner_stats = away.lineup_stats[runner.player_id]
    batter_stats = away.lineup_stats[batter.player_id]
    assert runner_stats.r == 1
    assert batter_stats.rbi == 1
    box = generate_boxscore(home, away)
    assert box["away"]["score"] == 1
    assert box["home"]["score"] == 0
    assert box["away"]["batting"][1]["so"] == 2
    assert box["home"]["pitching"][0]["pitches"] == 7


def test_walk_records_stats():
    cfg = load_config()
    batter = make_player("bat")
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    # four balls
    rng = MockRandom([0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9])
    sim = GameSimulation(home, away, cfg, rng)
    outs = sim.play_at_bat(away, home)
    assert outs == 0
    stats = away.lineup_stats[batter.player_id]
    pstats = home.current_pitcher_state
    assert stats.bb == 1
    assert stats.ab == 0
    assert stats.pa == 1
    assert pstats.walks == 1
    assert pstats.pitches_thrown == 4


def test_pitch_control_affects_location():
    cfg = load_config()
    batter1 = make_player("bat1")
    home_high = TeamState(
        lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp", control=70)]
    )
    away_high = TeamState(lineup=[batter1], bench=[], pitchers=[make_pitcher("ap")])
    rng_high = MockRandom([0.4, 0.9, 0.4, 0.9, 0.4, 0.9])
    sim_high = GameSimulation(home_high, away_high, cfg, rng_high)
    outs_high = sim_high.play_at_bat(away_high, home_high)
    assert outs_high == 1

    batter2 = make_player("bat2")
    home_low = TeamState(
        lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp", control=30)]
    )
    away_low = TeamState(lineup=[batter2], bench=[], pitchers=[make_pitcher("ap")])
    rng_low = MockRandom([0.8, 0.9, 0.8, 0.9, 0.8, 0.9, 0.8, 0.9])
    sim_low = GameSimulation(home_low, away_low, cfg, rng_low)
    outs_low = sim_low.play_at_bat(away_low, home_low)
    stats_low = away_low.lineup_stats[batter2.player_id]
    assert outs_low == 0
    assert stats_low.bb == 1


def test_pitch_around_ibb_in_simulation():
    cfg = make_cfg(
        pitchAroundChanceNoInn=0,
        pitchAroundChanceBase=0,
        pitchAroundChanceInn7Adjust=20,
        pitchAroundChanceOut2=20,
        pitchAroundChancePH2BatAdjust=40,
        pitchAroundChanceLowGFThresh=40,
        pitchAroundChanceLowGFAdjust=10,
        defManPitchAroundToIBBPct=100,
    )
    rng = MockRandom([0.0, 0.0])
    batter1 = make_player("b1", ph=90, gf=30)
    batter2 = make_player("b2", ph=10)
    away = TeamState(lineup=[batter1, batter2], bench=[], pitchers=[make_pitcher("ap")])
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away.inning_runs = [0] * 6
    away.bases[1] = BatterState(make_player("r2"))
    away.bases[2] = BatterState(make_player("r3"))
    sim = GameSimulation(home, away, cfg, rng)
    sim.current_outs = 2
    sim.play_at_bat(away, home)
    assert any("Intentional walk issued" in ev for ev in sim.debug_log)


def test_no_pitch_around_with_early_inning_or_outs():
    cfg = make_cfg(
        pitchAroundChanceNoInn=0,
        pitchAroundChanceBase=0,
        pitchAroundChanceInn7Adjust=40,
        pitchAroundChanceOut2=40,
        pitchAroundChanceOut0=-40,
        pitchAroundChancePH1BatAdjust=40,
        defManPitchAroundToIBBPct=100,
    )
    rng = MockRandom([0.0] * 40)
    batter1 = make_player("b1", ph=90)
    batter2 = make_player("b2", ph=10)
    away = TeamState(lineup=[batter1, batter2], bench=[], pitchers=[make_pitcher("ap")])
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    sim = GameSimulation(home, away, cfg, rng)
    sim.current_outs = 0  # Early in inning with no outs
    sim.play_at_bat(away, home)
    assert all("Intentional walk issued" not in ev for ev in sim.debug_log)
    assert all("Pitch around" not in ev for ev in sim.debug_log)


def test_fielding_stats_tracking():
    cfg = load_config()
    catcher = make_player("c")
    catcher.primary_position = "C"
    second = make_player("2")
    second.primary_position = "2B"
    defense = TeamState(
        lineup=[catcher, second], bench=[], pitchers=[make_pitcher("hp")]
    )
    runner = make_player("r", sp=80)
    offense = TeamState(lineup=[runner], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    runner_state.lead = 2
    offense.lineup_stats[runner.player_id] = runner_state
    offense.bases[0] = runner_state
    offense.base_pitchers[0] = defense.current_pitcher_state
    rng = MockRandom([0.9, 0.0, 0.9, 0.0, 0.9, 0.0, 0.9])
    sim = GameSimulation(defense, offense, cfg, rng)
    res = sim._attempt_steal(offense, defense, defense.current_pitcher_state.player, force=True)
    assert res is False
    outs = sim.play_at_bat(offense, defense)
    assert outs == 1
    c_fs = defense.fielding_stats[catcher.player_id]
    s_fs = defense.fielding_stats[second.player_id]
    p_fs = defense.fielding_stats[defense.current_pitcher_state.player.player_id]
    assert c_fs.cs == 1
    assert c_fs.sba == 1
    assert c_fs.a == 1
    assert c_fs.po == 1
    assert s_fs.po == 1
    assert p_fs.a == 1


def test_defensive_alignment_normal():
    cfg = load_config()
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    sim = GameSimulation(home, away, cfg, MockRandom([0.5]))
    sim._set_defensive_alignment(away, home, outs=0)
    assert sim.current_infield_situation == "normal"


def test_defensive_alignment_double_play():
    cfg = load_config()
    runner = BatterState(make_player("r1"))
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    away.lineup_stats[runner.player.player_id] = runner
    away.bases[0] = runner
    sim = GameSimulation(home, away, cfg, MockRandom([0.5]))
    sim._set_defensive_alignment(away, home, outs=0)
    assert sim.current_infield_situation == "doublePlay"


def test_defensive_alignment_guard_and_cutoff():
    cfg = load_config()
    runner = BatterState(make_player("r2"))
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    away.lineup_stats[runner.player.player_id] = runner
    away.bases[2] = runner

    # Close game -> guard lines
    home.runs = 1
    away.runs = 0
    sim = GameSimulation(home, away, cfg, MockRandom([0.5]))
    sim._set_defensive_alignment(away, home, outs=0)
    assert sim.current_infield_situation == "guardLines"

    # Not close -> cutoff run
    home.runs = 3
    away.runs = 0
    sim = GameSimulation(home, away, cfg, MockRandom([0.5]))
    sim._set_defensive_alignment(away, home, outs=0)
    assert sim.current_infield_situation == "cutoffRun"


def test_simulate_game_skips_bottom_when_home_leads():
    cfg = load_config()
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    sim = GameSimulation(home, away, cfg, random.Random())

    calls = []

    def fake_play_half(self, offense, defense):
        offense.inning_runs.append(0)
        calls.append(offense is self.home)

    sim._play_half = fake_play_half.__get__(sim, GameSimulation)
    home.runs = 1
    sim.simulate_game()

    assert calls.count(True) == 8
    assert calls.count(False) == 9


def test_simulate_game_goes_to_extra_innings_when_tied():
    cfg = load_config()
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    sim = GameSimulation(home, away, cfg, random.Random())

    def fake_play_half(self, offense, defense):
        inning = len(offense.inning_runs)
        if offense is self.away and inning == 9:
            offense.runs += 1
            offense.inning_runs.append(1)
        else:
            offense.inning_runs.append(0)

    sim._play_half = fake_play_half.__get__(sim, GameSimulation)
    sim.simulate_game()

    assert len(home.inning_runs) == 10
    assert len(away.inning_runs) == 10
    assert away.runs == 1
    assert home.runs == 0
