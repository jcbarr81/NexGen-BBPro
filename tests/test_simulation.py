import random

from logic.simulation import (
    BatterState,
    GameSimulation,
    TeamState,
    generate_boxscore,
)
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import load_config


class MockRandom(random.Random):
    """Deterministic random generator using a predefined sequence."""

    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def random(self):  # type: ignore[override]
        return self.values.pop(0)

    def randint(self, a, b):  # type: ignore[override]
        # ``PitcherAI`` uses ``randint`` for pitch variation.  Returning the
        # lower bound keeps behaviour deterministic without consuming the
        # predefined sequence.
        return a


def make_player(pid: str, ph: int = 50, sp: int = 50, ch: int = 50) -> Player:
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
        gf=50,
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
    pid: str, endurance: int = 100, hold_runner: int = 50, role: str = "SP"
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
        control=50,
        movement=50,
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
    assert stats.at_bats == 1


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
    assert stats.walks == 1


def test_steal_attempt_success():
    cfg = load_config()
    runner = make_player("run", ph=80, sp=90)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[runner], bench=[], pitchers=[make_pitcher("ap")])
    # pitch strike ->0, swing hit ->0, steal attempt ->0, steal success ->0
    rng = MockRandom([0.0, 0.0, 0.0, 0.0])
    sim = GameSimulation(home, away, cfg, rng)
    outs = sim.play_at_bat(away, home)
    assert outs == 0
    stats = away.lineup_stats["run"]
    assert stats.steals == 1
    assert away.bases[1] is stats


def test_steal_attempt_failure():
    cfg = load_config()
    runner = make_player("run")
    batter = make_player("bat", ph=80, sp=90)
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    runner_state = BatterState(runner)
    away.lineup_stats[runner.player_id] = runner_state
    away.bases[0] = runner_state
    cfg.values.update({"pitchOutChanceBase": 0})
    # hnr success ->0.0, steal failure ->0.9, pitch strike ->0.0, swing hit ->0.0, post-hit steal attempt fails ->1.0
    rng = MockRandom([0.0, 0.9, 0.0, 0.0, 1.0])
    sim = GameSimulation(home, away, cfg, rng)
    outs = sim.play_at_bat(away, home)
    assert outs == 1
    assert away.bases[0] is not None


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
    assert outs == 3
    assert away.runs == 1
    assert away.inning_runs == [1]
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
    assert stats.walks == 1
    assert stats.at_bats == 0
    assert pstats.walks == 1
    assert pstats.pitches_thrown == 4
