import random

from logic.simulation import GameSimulation, TeamState, BatterState
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import make_cfg


class MockRandom(random.Random):
    """Deterministic random generator using a predefined sequence."""

    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def random(self):  # type: ignore[override]
        return self.values.pop(0)

    def randint(self, a, b):  # type: ignore[override]
        # ``PitcherAI`` uses ``randint`` for pitch variation.  Returning the
        # lower bound keeps the predefined sequence for ``random`` intact.
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


def make_pitcher(pid: str) -> Pitcher:
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
        endurance=100,
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


def test_swing_result_respects_bat_speed():
    # Low bat speed -> out
    cfg_slow = make_cfg(swingSpeedBase=10)
    batter1 = make_player("b1")
    home1 = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp1")])
    away1 = TeamState(lineup=[batter1], bench=[], pitchers=[make_pitcher("ap1")])
    rng1 = MockRandom([0.2, 0.9])
    sim1 = GameSimulation(home1, away1, cfg_slow, rng1)
    outs1 = sim1.play_at_bat(away1, home1)
    assert outs1 == 1
    assert away1.lineup_stats["b1"].hits == 0

    # High bat speed -> hit
    cfg_fast = make_cfg(swingSpeedBase=80)
    batter2 = make_player("b2")
    home2 = TeamState(lineup=[make_player("h2")], bench=[], pitchers=[make_pitcher("hp2")])
    away2 = TeamState(lineup=[batter2], bench=[], pitchers=[make_pitcher("ap2")])
    rng2 = MockRandom([0.2, 0.9])
    sim2 = GameSimulation(home2, away2, cfg_fast, rng2)
    outs2 = sim2.play_at_bat(away2, home2)
    assert outs2 == 0
    assert away2.lineup_stats["b2"].hits == 1


def test_runner_advancement_respects_speed():
    batter1 = make_player("bat1", ph=80)
    runner1 = make_player("run1", sp=50)
    runner_state1 = BatterState(runner1)
    home1 = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp1")])
    away1 = TeamState(lineup=[batter1], bench=[], pitchers=[make_pitcher("ap1")])
    away1.lineup_stats[runner1.player_id] = runner_state1
    away1.bases[0] = runner_state1

    cfg_slow = make_cfg(speedBase=10)
    rng1 = MockRandom([0.0, 0.9])
    sim1 = GameSimulation(home1, away1, cfg_slow, rng1)
    outs1 = sim1.play_at_bat(away1, home1)
    assert outs1 == 0
    assert away1.bases[1] is runner_state1
    assert away1.bases[2] is None

    batter2 = make_player("bat2", ph=80)
    runner2 = make_player("run2", sp=50)
    runner_state2 = BatterState(runner2)
    home2 = TeamState(lineup=[make_player("h2")], bench=[], pitchers=[make_pitcher("hp2")])
    away2 = TeamState(lineup=[batter2], bench=[], pitchers=[make_pitcher("ap2")])
    away2.lineup_stats[runner2.player_id] = runner_state2
    away2.bases[0] = runner_state2

    cfg_fast = make_cfg(speedBase=30)
    rng2 = MockRandom([0.0, 0.9])
    sim2 = GameSimulation(home2, away2, cfg_fast, rng2)
    outs2 = sim2.play_at_bat(away2, home2)
    assert outs2 == 0
    assert away2.bases[2] is runner_state2
