import math
import random

from logic.simulation import (
    BatterState,
    GameSimulation,
    TeamState,
)
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import load_config


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


def test_team_lob_and_events_recorded():
    cfg = load_config()
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    sim = GameSimulation(home, away, cfg, random.Random())

    runner = BatterState(away.lineup[0])
    away.bases[0] = runner

    def fake_play_at_bat(self, offense, defense):
        self.debug_log.append("event")
        return 1

    sim.play_at_bat = fake_play_at_bat.__get__(sim, GameSimulation)
    sim._play_half(away, home)

    assert away.lob == 1
    assert away.inning_lob == [1]
    assert away.inning_events[0] == ["event", "event", "event"]


def test_team_stats_computed():
    cfg = load_config()
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    sim = GameSimulation(home, away, cfg, random.Random())

    home.runs = 3
    away.runs = 1
    home.lob = 2
    away.lob = 1

    away_bs = BatterState(make_player("a1"))
    away_bs.pa = 10
    away_bs.ab = 9
    away_bs.h = 2
    away_bs.b1 = 2
    away_bs.bb = 1
    away_bs.so = 5
    away_bs.roe = 1
    away.lineup_stats = {"a1": away_bs}

    home_bs = BatterState(make_player("h1"))
    home_bs.pa = 8
    home_bs.ab = 8
    home_bs.h = 1
    home_bs.b1 = 1
    home_bs.so = 7
    home.lineup_stats = {"h1": home_bs}

    sim.simulate_game(innings=0)

    assert home.team_stats["g"] == 1
    assert home.team_stats["r"] == 3
    assert home.team_stats["ra"] == 1
    assert home.team_stats["lob"] == 2
    assert math.isclose(home.team_stats["der"], 0.25)
    assert math.isclose(home.team_stats["rpg"], 3.0)
    assert math.isclose(home.team_stats["rag"], 1.0)

    assert away.team_stats["g"] == 1
    assert away.team_stats["r"] == 1
    assert away.team_stats["ra"] == 3
    assert math.isclose(away.team_stats["rpg"], 1.0)
    assert math.isclose(away.team_stats["rag"], 3.0)
