import random

from logic.simulation import GameSimulation, TeamState
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import make_cfg


class ZeroRandom(random.Random):
    """Deterministic random source returning 0 for all calls."""

    def random(self):  # type: ignore[override]
        return 0.0

    def randint(self, a, b):  # type: ignore[override]
        return a


def _player(pid: str) -> Player:
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


def _pitcher(pid: str) -> Pitcher:
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


def test_ball_in_play_outs_forces_out():
    cfg = make_cfg(
        groundBallBaseRate=100,
        flyBallBaseRate=0,
        lineDriveBaseRate=0,
        groundOutProb=0.0,
        lineOutProb=0.0,
        flyOutProb=0.0,
        hitProbCap=1.0,
        foulPitchBasePct=0,
        ballInPlayPitchPct=100,
        ballInPlayOuts=1.0,
    )
    home = TeamState(lineup=[_player("h1")], bench=[], pitchers=[_pitcher("hp")])
    away = TeamState(lineup=[_player("a1")], bench=[], pitchers=[_pitcher("ap")])
    rng = ZeroRandom()
    sim = GameSimulation(home, away, cfg, rng)
    outs = sim.play_at_bat(away, home)
    assert outs == 1
    pitcher_state = home.current_pitcher_state
    assert pitcher_state is not None
    batter_state = away.lineup_stats[away.lineup[0].player_id]
    assert batter_state.pitches >= 1
    assert all(b is None for b in away.bases)
