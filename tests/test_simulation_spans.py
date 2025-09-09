import random

from logic.season_simulator import (
    SeasonSimulator,
    simulate_day,
    simulate_week,
    simulate_month,
    simulate_season,
)
from logic.simulation import TeamState, simulate_game
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
        endurance=50,
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


def _build_game_cb(cfg, teams):
    def _cb(home_id: str, away_id: str):
        home_info = teams[home_id]
        away_info = teams[away_id]
        home = TeamState(list(home_info["lineup"]), list(home_info["bench"]), list(home_info["pitchers"]))
        away = TeamState(list(away_info["lineup"]), list(away_info["bench"]), list(away_info["pitchers"]))
        simulate_game(home, away, cfg, random.Random(0), innings=1)
        return home.runs, away.runs

    return _cb


def test_span_helpers_accumulate_stats():
    cfg = load_config()
    h_lineup = [make_player("h1")]
    a_lineup = [make_player("a1")]
    h_pitchers = [make_pitcher("hp")]
    a_pitchers = [make_pitcher("ap")]
    teams = {
        "H": {"lineup": h_lineup, "bench": [], "pitchers": h_pitchers},
        "A": {"lineup": a_lineup, "bench": [], "pitchers": a_pitchers},
    }
    schedule = [
        {"date": "2024-04-01", "home": "H", "away": "A"},
        {"date": "2024-04-02", "home": "A", "away": "H"},
        {"date": "2024-04-03", "home": "H", "away": "A"},
        {"date": "2024-04-04", "home": "A", "away": "H"},
    ]
    sim = SeasonSimulator(schedule, simulate_game=_build_game_cb(cfg, teams))

    simulate_day(sim)
    pa_after_day = h_lineup[0].season_stats.get("pa", 0)
    assert pa_after_day > 0

    simulate_week(sim)
    pa_after_week = h_lineup[0].season_stats.get("pa", 0)
    assert pa_after_week > pa_after_day

    simulate_month(sim)
    assert h_lineup[0].season_stats.get("pa", 0) == pa_after_week

    simulate_season(sim)
    assert h_lineup[0].season_stats.get("pa", 0) == pa_after_week


def test_simulate_season_runs_all_games():
    cfg = load_config()
    h_lineup = [make_player("hh1")]
    a_lineup = [make_player("aa1")]
    h_pitchers = [make_pitcher("hhp")]
    a_pitchers = [make_pitcher("aap")]
    teams = {
        "H": {"lineup": h_lineup, "bench": [], "pitchers": h_pitchers},
        "A": {"lineup": a_lineup, "bench": [], "pitchers": a_pitchers},
    }
    schedule = [
        {"date": "2024-04-01", "home": "H", "away": "A"},
        {"date": "2024-04-02", "home": "A", "away": "H"},
        {"date": "2024-04-03", "home": "H", "away": "A"},
        {"date": "2024-04-04", "home": "A", "away": "H"},
    ]
    sim = SeasonSimulator(schedule, simulate_game=_build_game_cb(cfg, teams))

    simulate_season(sim)
    assert sim._index == len(sim.dates)
    assert h_lineup[0].season_stats.get("pa", 0) > 0
