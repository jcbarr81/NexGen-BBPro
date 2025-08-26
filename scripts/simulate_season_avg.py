"""Simulate a full 162-game season and report average box score stats.

For lengthy runs this script can benefit from PyPy's JIT or by invoking
CPython with ``python -O`` to skip asserts. When using PyPy ensure required
C extensions such as ``bcrypt`` are available; GUI-focused modules like
``PyQt6`` are not needed here.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date
from pathlib import Path
import argparse
import os
import random
import sys

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover
    def tqdm(iterable, **kwargs):
        return iterable

# Ensure project root is on the path when running this script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from logic.schedule_generator import generate_mlb_schedule
from logic.season_simulator import SeasonSimulator
from logic.simulation import (
    FieldingState,
    GameSimulation,
    PitcherState,
    TeamState,
    generate_boxscore,
)
from logic.playbalance_config import PlayBalanceConfig
from utils.lineup_loader import build_default_game_state
from utils.path_utils import get_base_dir
from utils.team_loader import load_teams


STAT_ORDER = [
    "Runs",
    "Hits",
    "Doubles",
    "Triples",
    "HomeRuns",
    "Walks",
    "Strikeouts",
    "StolenBases",
    "CaughtStealing",
    "HitByPitch",
    "TotalPitchesThrown",
    "Strikes",
]


def clone_team_state(base: TeamState) -> TeamState:
    """Return a deep-copied ``TeamState`` with per-game fields reset."""

    team = deepcopy(base)
    team.lineup_stats = {}
    team.pitcher_stats = {}
    team.fielding_stats = {}
    team.batting_index = 0
    team.bases = [None, None, None]
    team.base_pitchers = [None, None, None]
    team.runs = 0
    team.inning_runs = []
    team.lob = 0
    team.inning_lob = []
    team.inning_events = []
    team.team_stats = {}
    team.warming_reliever = False
    team.bullpen_warmups = {}
    if team.pitchers:
        starter = team.pitchers[0]
        state = PitcherState(starter)
        team.pitcher_stats[starter.player_id] = state
        team.current_pitcher_state = state
        state.g += 1
        state.gs += 1
        fs = team.fielding_stats.setdefault(starter.player_id, FieldingState(starter))
        fs.g += 1
        fs.gs += 1
    else:
        team.current_pitcher_state = None
    for p in team.lineup:
        fs = team.fielding_stats.setdefault(p.player_id, FieldingState(p))
        fs.g += 1
        fs.gs += 1
    return team


def simulate_season_average(use_tqdm: bool = True) -> None:
    """Run a season simulation and print average box score values.

    Args:
        use_tqdm: Whether to display a progress bar using ``tqdm``.
    """

    teams = [t.team_id for t in load_teams()]
    schedule = generate_mlb_schedule(teams, date(2025, 4, 1))
    base_states = {tid: build_default_game_state(tid) for tid in teams}

    cfg = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")
    cfg.ballInPlayOuts = 1
    rng = random.Random(42)

    totals: Counter[str] = Counter()
    total_games = 0

    def simulate_game(home_id: str, away_id: str) -> tuple[int, int]:
        nonlocal total_games

        home = clone_team_state(base_states[home_id])
        away = clone_team_state(base_states[away_id])
        sim = GameSimulation(home, away, cfg, rng)
        sim.simulate_game()
        box = generate_boxscore(home, away)

        for side in ("home", "away"):
            batting = box[side]["batting"]
            pitching = box[side]["pitching"]
            totals["Runs"] += box[side]["score"]
            totals["Hits"] += sum(p["h"] for p in batting)
            totals["Doubles"] += sum(p["2b"] for p in batting)
            totals["Triples"] += sum(p["3b"] for p in batting)
            totals["HomeRuns"] += sum(p["hr"] for p in batting)
            totals["Walks"] += sum(p["bb"] for p in batting)
            totals["Strikeouts"] += sum(p["so"] for p in batting)
            totals["StolenBases"] += sum(p["sb"] for p in batting)
            totals["CaughtStealing"] += sum(p["cs"] for p in batting)
            totals["HitByPitch"] += sum(p["hbp"] for p in batting)
            totals["TotalPitchesThrown"] += sum(p["pitches"] for p in pitching)
            totals["Strikes"] += sum(p["strikes"] for p in pitching)

        total_games += 1
        return box["home"]["score"], box["away"]["score"]

    simulator = SeasonSimulator(schedule, simulate_game=simulate_game)
    iterator = range(len(simulator.dates))
    if use_tqdm:
        iterator = tqdm(iterator, desc="Simulating season")
    for _ in iterator:
        simulator.simulate_next_day()

    averages = {k: totals[k] / total_games for k in STAT_ORDER}

    print("Average box score per game (both teams):")
    for key in STAT_ORDER:
        print(f"{key}: {averages[key]:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simulate a full season and report average box score stats."
    )
    parser.add_argument(
        "--disable-tqdm",
        action="store_true",
        help="Disable tqdm progress bar.",
    )
    args = parser.parse_args()

    env_disable = os.getenv("DISABLE_TQDM", "").lower() in {"1", "true", "yes"}
    use_tqdm = not (args.disable_tqdm or env_disable)
    simulate_season_average(use_tqdm=use_tqdm)
