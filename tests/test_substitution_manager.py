import random

from logic.simulation import BatterState, TeamState
from logic.substitution_manager import SubstitutionManager
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import load_config, make_cfg


class MockRandom(random.Random):
    """Deterministic random generator using a predefined sequence."""

    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def random(self):  # type: ignore[override]
        return self.values.pop(0)


def make_player(
    pid: str,
    ph: int = 50,
    sp: int = 50,
    gf: int = 50,
    ch: int = 50,
    fa: int = 0,
    arm: int = 0,
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
        fa=fa,
        arm=arm,
    )


def make_pitcher(pid: str, endurance: int = 100) -> Pitcher:
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
        arm=50,
        fa=50,
        role="SP",
    )
def test_pinch_hit():
    cfg = load_config()
    cfg.values.update({"doubleSwitchPHAdjust": 100})
    bench = make_player("bench", ph=80)
    starter = make_player("start", ph=10)
    team = TeamState(lineup=[starter], bench=[bench], pitchers=[make_pitcher("p")])
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_pinch_hit(team, 0, [])
    assert player.player_id == "bench"
    assert team.lineup[0].player_id == "bench"


def test_pinch_hit_need_hit():
    cfg = load_config()
    cfg.values.update({"phForHitBase": 100})
    bench = make_player("bench", ph=80, ch=80)
    starter = make_player("start", ph=10, ch=10)
    deck = make_player("deck")
    team = TeamState(lineup=[starter, deck], bench=[bench], pitchers=[make_pitcher("p")])
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_pinch_hit_need_hit(
        team,
        0,
        1,
        inning=9,
        outs=1,
        run_diff=-1,
        home_team=False,
        log=[],
    )
    assert player.player_id == "bench"
    assert team.lineup[0].player_id == "bench"


def test_pinch_hit_need_hit_rating_adjust():
    cfg = make_cfg(
        phForHitBase=0,
        phForHitVeryHighBatRatThresh=1000,
        phForHitHighBatRatThresh=1000,
        phForHitMedBatRatThresh=1000,
        phForHitLowBatRatThresh=0,
        phForHitLowBatRatAdjust=100,
        phForHitVeryLowBatRatAdjust=0,
    )
    bench = make_player("bench", ph=80, ch=80)
    starter = make_player("start", ph=10, ch=10)
    deck = make_player("deck", ph=50, ch=50)
    team = TeamState(lineup=[starter, deck], bench=[bench], pitchers=[make_pitcher("p")])
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_pinch_hit_need_hit(
        team,
        0,
        1,
        inning=1,
        outs=0,
        run_diff=0,
        home_team=False,
        log=[],
    )
    assert player.player_id == "bench"
    assert team.lineup[0].player_id == "bench"


def test_pinch_hit_need_run():
    cfg = load_config()
    cfg.values.update({"phForRunBase": 100})
    bench = make_player("bench", ph=80, ch=80)
    starter = make_player("start", ph=10, ch=10)
    deck = make_player("deck")
    team = TeamState(
        lineup=[starter, deck], bench=[bench], pitchers=[make_pitcher("p1")]
    )
    defense = TeamState(
        lineup=[make_player("d")], bench=[], pitchers=[make_pitcher("p2")]
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_pinch_hit_need_run(
        team,
        defense,
        0,
        1,
        inning=9,
        outs=1,
        run_diff=-1,
        home_team=False,
        log=[],
    )
    assert player.player_id == "bench"
    assert team.lineup[0].player_id == "bench"


def test_pinch_hit_need_run_rating_adjust():
    cfg = make_cfg(
        phForRunBase=0,
        phForRunVeryHighBatRatThresh=1000,
        phForRunHighBatRatThresh=1000,
        phForRunMedBatRatThresh=1000,
        phForRunLowBatRatThresh=0,
        phForRunLowBatRatAdjust=100,
        phForRunVeryLowBatRatAdjust=0,
    )
    bench = make_player("bench", ph=80, ch=80)
    starter = make_player("start", ph=10, ch=10)
    deck = make_player("deck", ph=50, ch=50)
    team = TeamState(
        lineup=[starter, deck], bench=[bench], pitchers=[make_pitcher("p1")]
    )
    defense = TeamState(
        lineup=[make_player("d")], bench=[], pitchers=[make_pitcher("p2")]
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_pinch_hit_need_run(
        team,
        defense,
        0,
        1,
        inning=1,
        outs=0,
        run_diff=0,
        home_team=False,
        log=[],
    )
    assert player.player_id == "bench"
    assert team.lineup[0].player_id == "bench"


def test_pinch_hit_need_run_platoon():
    cfg = load_config()
    cfg.values.update({"phForRunPHPlatAdvAdjust": 100})
    bench = make_player("bench", ph=80, ch=80)
    bench.bats = "L"
    starter = make_player("start", ph=10, ch=10)
    starter.bats = "R"
    deck = make_player("deck")
    team = TeamState(
        lineup=[starter, deck], bench=[bench], pitchers=[make_pitcher("p1")]
    )
    defense = TeamState(
        lineup=[make_player("d")], bench=[], pitchers=[make_pitcher("p2")]
    )
    defense.pitchers[0].bats = "R"
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_pinch_hit_need_run(
        team,
        defense,
        0,
        1,
        inning=9,
        outs=1,
        run_diff=-1,
        home_team=False,
        log=[],
    )
    assert player.player_id == "bench"
    assert team.lineup[0].player_id == "bench"


def test_pinch_run():
    cfg = load_config()
    cfg.values.update({"prChanceOnFirstBase": 100})
    runner = make_player("slow", sp=10)
    fast = make_player("fast", sp=90)
    team = TeamState(lineup=[runner], bench=[fast], pitchers=[make_pitcher("p")])
    state = BatterState(runner)
    team.bases[0] = state
    team.lineup_stats[runner.player_id] = state
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    mgr.maybe_pinch_run(team, base=0, inning=1, outs=0, run_diff=0, log=[])
    assert team.bases[0].player.player_id == "fast"
    assert team.lineup[0].player_id == "fast"


def test_pinch_run_insignificant():
    cfg = load_config()
    cfg.values.update({"prChanceOnFirstBase": 100, "prChanceInsignificant": -100})
    runner = make_player("slow", sp=10)
    fast = make_player("fast", sp=90)
    team = TeamState(lineup=[runner], bench=[fast], pitchers=[make_pitcher("p")])
    state = BatterState(runner)
    team.bases[0] = state
    team.lineup_stats[runner.player_id] = state
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    mgr.maybe_pinch_run(team, base=0, inning=1, outs=0, run_diff=-2, log=[])
    assert team.bases[0].player.player_id == "slow"
    assert team.lineup[0].player_id == "slow"


def test_defensive_sub_injury_inning():
    cfg = load_config()
    cfg.values.update(
        {
            "defSubBase": 0,
            "defSubAfterInn8Adjust": 50,
            "defSubPerInjuryPointAdjust": 50,
            "defSubBeforeInn7Adjust": 0,
            "defSubInn7Adjust": 0,
            "defSubInn8Adjust": 0,
            # Disable rating based adjustments to focus on modifiers
            "defSubVeryHighCurrDefAdjust": 0,
            "defSubHighCurrDefAdjust": 0,
            "defSubMedCurrDefAdjust": 0,
            "defSubLowCurrDefAdjust": 0,
            "defSubVeryLowCurrDefAdjust": 0,
            "defSubVeryHighNewDefAdjust": 0,
            "defSubHighNewDefAdjust": 0,
            "defSubMedNewDefAdjust": 0,
            "defSubLowNewDefAdjust": 0,
            "defSubVeryLowNewDefAdjust": 0,
        }
    )
    weak = make_player("weak", fa=10, arm=10)
    weak.injured = True
    strong = make_player("strong", fa=90, arm=90)
    team = TeamState(lineup=[weak], bench=[strong], pitchers=[make_pitcher("p")])
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    mgr.maybe_defensive_sub(team, inning=9, log=[])
    assert team.lineup[0].player_id == "strong"


def test_defensive_sub_position_qualification():
    cfg = load_config()
    cfg.values.update(
        {
            "defSubBase": 0,
            "defSubVeryLowCurrDefAdjust": 50,
            "defSubVeryHighNewDefAdjust": 50,
            "defSubNoQualifiedPosAdjust": -100,
            "defSubBeforeInn7Adjust": 0,
            "defSubInn7Adjust": 0,
            "defSubInn8Adjust": 0,
            "defSubAfterInn8Adjust": 0,
        }
    )
    weak = make_player("weak", fa=10, arm=10)
    strong = make_player("strong", fa=90, arm=90)
    strong.primary_position = "2B"
    strong.other_positions = []
    team = TeamState(lineup=[weak], bench=[strong], pitchers=[make_pitcher("p")])
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    mgr.maybe_defensive_sub(team, inning=9, log=[])
    assert team.lineup[0].player_id == "weak"


def test_defensive_sub_defense_thresholds():
    cfg = load_config()
    cfg.values.update(
        {
            "defSubBase": 0,
            "defSubBeforeInn7Adjust": 0,
            "defSubInn7Adjust": 0,
            "defSubInn8Adjust": 0,
            "defSubAfterInn8Adjust": 0,
            "defSubVeryLowCurrDefAdjust": 50,
            "defSubVeryHighNewDefAdjust": 50,
        }
    )
    weak = make_player("weak", fa=10, arm=10)
    strong = make_player("strong", fa=90, arm=90)
    team = TeamState(lineup=[weak], bench=[strong], pitchers=[make_pitcher("p")])
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    mgr.maybe_defensive_sub(team, inning=9, log=[])
    assert team.lineup[0].player_id == "strong"


def test_double_switch():
    cfg = load_config()
    cfg.values.update({"doubleSwitchBase": 0, "doubleSwitchPHAdjust": 100})
    bench_hitter = make_player("bench", ph=80)
    starter = make_player("start", ph=10)
    offense = TeamState(lineup=[starter], bench=[bench_hitter], pitchers=[make_pitcher("op")])
    defense = TeamState(
        lineup=[make_player("d")],
        bench=[],
        pitchers=[make_pitcher("p1", endurance=5), make_pitcher("p2")],
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_double_switch(offense, defense, 0, log=[])
    assert player and player.player_id == "bench"
    assert offense.lineup[0].player_id == "bench"
    assert defense.current_pitcher_state.player.player_id == "p2"


def test_double_switch_pitcher_due():
    cfg = load_config()
    cfg.values.update({"doubleSwitchBase": 0, "doubleSwitchPitcherDueAdjust": 100})
    bench_hitter = make_player("bench", ph=80)
    starter = make_player("start", ph=10)
    offense = TeamState(lineup=[starter], bench=[bench_hitter], pitchers=[make_pitcher("op")])
    defense = TeamState(
        lineup=[make_player("d")],
        bench=[],
        pitchers=[make_pitcher("p1", endurance=5), make_pitcher("p2")],
        batting_index=1,
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_double_switch(offense, defense, 0, log=[])
    assert player and player.player_id == "bench"
    assert offense.lineup[0].player_id == "bench"
    assert defense.current_pitcher_state.player.player_id == "p2"


def test_double_switch_position_qualification():
    cfg = load_config()
    cfg.values.update(
        {
            "doubleSwitchBase": 100,
            "doubleSwitchNoQualifiedPosAdjust": -100,
        }
    )
    bench_hitter = make_player("bench", ph=80)
    bench_hitter.primary_position = "2B"
    starter = make_player("start", ph=10)
    offense = TeamState(lineup=[starter], bench=[bench_hitter], pitchers=[make_pitcher("op")])
    defense = TeamState(
        lineup=[make_player("d")],
        bench=[],
        pitchers=[make_pitcher("p1", endurance=5), make_pitcher("p2")],
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_double_switch(offense, defense, 0, log=[])
    assert player is None
    assert offense.lineup[0].player_id == "start"
    assert defense.current_pitcher_state.player.player_id == "p1"


def test_double_switch_curr_def_blocks():
    cfg = load_config()
    cfg.values.update(
        {
            "doubleSwitchBase": 50,
            "doubleSwitchVeryHighCurrDefThresh": 0,
            "doubleSwitchVeryHighCurrDefAdjust": -100,
        }
    )
    bench_hitter = make_player("bench", ph=80, fa=10, arm=10)
    starter = make_player("start", ph=10, fa=90, arm=90)
    offense = TeamState(lineup=[starter], bench=[bench_hitter], pitchers=[make_pitcher("op")])
    defense = TeamState(
        lineup=[make_player("d")],
        bench=[],
        pitchers=[make_pitcher("p1", endurance=5), make_pitcher("p2")],
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_double_switch(offense, defense, 0, log=[])
    assert player is None
    assert offense.lineup[0].player_id == "start"
    assert defense.current_pitcher_state.player.player_id == "p1"


def test_double_switch_new_def_bonus():
    cfg = load_config()
    cfg.values.update(
        {
            "doubleSwitchBase": 0,
            "doubleSwitchVeryHighNewDefThresh": 0,
            "doubleSwitchVeryHighNewDefAdjust": 100,
        }
    )
    bench_hitter = make_player("bench", ph=80, fa=90, arm=90)
    starter = make_player("start", ph=10, fa=10, arm=10)
    offense = TeamState(lineup=[starter], bench=[bench_hitter], pitchers=[make_pitcher("op")])
    defense = TeamState(
        lineup=[make_player("d")],
        bench=[],
        pitchers=[make_pitcher("p1", endurance=5), make_pitcher("p2")],
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_double_switch(offense, defense, 0, log=[])
    assert player and player.player_id == "bench"
    assert offense.lineup[0].player_id == "bench"
    assert defense.current_pitcher_state.player.player_id == "p2"


def test_change_pitcher():
    cfg = load_config()
    defense = TeamState(
        lineup=[make_player("d")],
        bench=[],
        pitchers=[make_pitcher("p1", endurance=5), make_pitcher("p2")],
    )
    mgr = SubstitutionManager(cfg, MockRandom([]))
    assert mgr.maybe_change_pitcher(defense, log=[])
    assert defense.current_pitcher_state.player.player_id == "p2"


def test_pinch_hit_for_pitcher():
    cfg = load_config()
    cfg.values.update(
        {
            "phForPitcherBase": 100,
            "phForPitcherEarlyInnAdjust": 0,
            "phForPitcherMiddleInnAdjust": 0,
            "phForPitcherLateInnAdjust": 0,
            "phForPitcherInn9Adjust": 0,
            "phForPitcherExtraInnAdjust": 0,
            "phForPitcherPerOutAdjust": 0,
            "phForPitcherPerBPPitcherAdjust": 0,
            "phForPitcherPerBenchPlayerAdjust": 0,
            "phForPitcherBigLeadAdjust": 0,
            "phForPitcherLeadAdjust": 0,
            "phForPitcherWinRunInScoringPosAdjust": 0,
            "phForPitcherWinRunOnFirstAdjust": 0,
            "phForPitcherWinRunAtBatAdjust": 0,
            "phForPitcherWinRunOnDeckAdjust": 0,
            "phForPitcherWinRunInDugoutAdjust": 0,
            "phForPitcherExhaustedAdjust": 0,
            "phForPitcherTiredAdjust": 0,
            "phForPitcherRestedAdjust": 0,
            "phForPitcherShutoutAdjust": 0,
            "phForPitcherNoHitterAdjust": 0,
            "phForPitcherPerInjuryPointAdjust": 0,
            "pitcherTiredThresh": 0,
        }
    )
    starter = make_pitcher("p1")
    reliever = make_pitcher("p2")
    bench_hitter = make_player("b", ph=80)
    offense = TeamState(
        lineup=[starter], bench=[bench_hitter], pitchers=[starter, reliever]
    )
    defense = TeamState(
        lineup=[make_player("d")], bench=[], pitchers=[make_pitcher("dp")]
    )
    mgr = SubstitutionManager(cfg, MockRandom([0.0]))
    player = mgr.maybe_pinch_hit_for_pitcher(
        offense, defense, 0, inning=1, outs=0, log=[]
    )
    assert player.player_id == "b"
    assert offense.lineup[0].player_id == "b"
    assert offense.current_pitcher_state.player.player_id == "p2"

