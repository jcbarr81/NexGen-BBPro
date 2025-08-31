import random

from logic.field_geometry import Stadium
from logic.simulation import (
    BatterState,
    GameSimulation,
    PitcherState,
    TeamState,
)
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import make_cfg


def make_player(pid: str, ph: int = 50) -> Player:
    return Player(
        player_id=pid,
        first_name=f"F{pid}",
        last_name=f"L{pid}",
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="1B",
        other_positions=[],
        gf=50,
        ch=50,
        ph=ph,
        sp=50,
        pl=0,
        vl=0,
    )


def make_pitcher(pid: str) -> Pitcher:
    return Pitcher(
        player_id=pid,
        first_name=f"PF{pid}",
        last_name=f"PL{pid}",
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
    )


def test_custom_stadium_affects_hit_value(monkeypatch):
    batter = make_player("b", ph=80)
    pitcher = make_pitcher("p")
    home = TeamState(lineup=[make_player("h")], bench=[], pitchers=[pitcher])
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    cfg = make_cfg(swingSpeedBase=80, averagePitchSpeed=50)

    sim = GameSimulation(home, away, cfg, random.Random())
    monkeypatch.setattr(sim.fielding_ai, "catch_action", lambda *a, **k: "no_attempt")
    monkeypatch.setattr(
        sim.physics, "landing_point", lambda vx, vy, vz: (250.0, 250.0, 1.0)
    )
    monkeypatch.setattr(sim.physics, "ball_roll_distance", lambda *a, **k: 0.0)
    monkeypatch.setattr(sim.physics, "ball_bounce", lambda *a, **k: (0.0, 0.0))

    b_state = BatterState(batter)
    p_state = PitcherState(pitcher)
    bases, _ = sim._swing_result(
        batter, pitcher, home, b_state, p_state, pitch_speed=50, rand=0.0
    )
    assert bases == 3

    small = Stadium(left=300.0, center=300.0, right=300.0)
    sim_small = GameSimulation(home, away, cfg, random.Random(), stadium=small)
    monkeypatch.setattr(sim_small.fielding_ai, "catch_action", lambda *a, **k: "no_attempt")
    monkeypatch.setattr(
        sim_small.physics, "landing_point", lambda vx, vy, vz: (250.0, 250.0, 1.0)
    )
    monkeypatch.setattr(sim_small.physics, "ball_roll_distance", lambda *a, **k: 0.0)
    monkeypatch.setattr(
        sim_small.physics, "ball_bounce", lambda *a, **k: (0.0, 0.0)
    )

    b_state = BatterState(batter)
    p_state = PitcherState(pitcher)
    bases_small, _ = sim_small._swing_result(
        batter, pitcher, home, b_state, p_state, pitch_speed=50, rand=0.0
    )
    assert bases_small == 4

