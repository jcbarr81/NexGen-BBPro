import random

from playbalance.simulation import GameSimulation, TeamState
from models.player import Player
from models.pitcher import Pitcher
from playbalance.playbalance_config import PlayBalanceConfig


def make_player(pid: str) -> Player:
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
        ch=50,
        ph=50,
        sp=50,
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
        endurance=10,
        control=80,
        movement=70,
        hold_runner=50,
        fb=99,
        cu=0,
        cb=0,
        sl=0,
        si=0,
        scb=0,
        kn=0,
        arm=90,
        fa=50,
        role="SP",
    )


def make_cfg() -> PlayBalanceConfig:
    return PlayBalanceConfig.from_dict(
        {
            "pitcherTiredThresh": 1,
            "pitcherExhaustedThresh": 0,
            "tiredPitchRatPct": 50,
            "tiredASPct": 80,
            "exhaustedPitchRatPct": 25,
            "exhaustedASPct": 60,
            "effCOPct": 90,
            "effMOPct": 80,
        }
    )


def setup_sim():
    cfg = make_cfg()
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("p1")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("p2")])
    sim = GameSimulation(home, away, cfg, random.Random(0))
    return sim, home.current_pitcher_state


def test_ratings_drop_when_tired():
    sim, ps = setup_sim()
    ps.pitches_thrown = ps.player.endurance - 1
    sim._update_fatigue(ps)
    fatigued = sim._fatigued_pitcher(ps.player)
    assert ps.player.fatigue == "tired"
    assert fatigued.fb == 49  # 99 * 0.5
    assert fatigued.arm == 72  # 90 * 0.8
    assert fatigued.control == 72  # 80 * 0.9
    assert fatigued.movement == 56  # 70 * 0.8


def test_ratings_drop_when_exhausted():
    sim, ps = setup_sim()
    ps.pitches_thrown = ps.player.endurance
    sim._update_fatigue(ps)
    fatigued = sim._fatigued_pitcher(ps.player)
    assert ps.player.fatigue == "exhausted"
    assert fatigued.fb == 24  # 99 * 0.25
    assert fatigued.arm == 54  # 90 * 0.6
    assert fatigued.control == 72  # effCOPct still 0.9
    assert fatigued.movement == 56  # effMOPct 0.8
