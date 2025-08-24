"""Simulate a full 162-game season and report average box score stats."""

from __future__ import annotations

from collections import Counter
from datetime import date
import random

from logic.schedule_generator import generate_mlb_schedule
from logic.season_simulator import SeasonSimulator
from logic.simulation import GameSimulation, generate_boxscore
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


def simulate_season_average() -> None:
    """Run a season simulation and print average box score values."""

    teams = [t.team_id for t in load_teams()]
    schedule = generate_mlb_schedule(teams, date(2025, 4, 1))

    cfg = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")
    rng = random.Random(42)

    totals: Counter[str] = Counter()
    total_games = 0

    def simulate_game(home_id: str, away_id: str) -> tuple[int, int]:
        nonlocal total_games

        home = build_default_game_state(home_id)
        away = build_default_game_state(away_id)
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
    for _ in range(len(simulator.dates)):
        simulator.simulate_next_day()

    averages = {k: totals[k] / total_games for k in STAT_ORDER}

    print("Average box score per game (both teams):")
    for key in STAT_ORDER:
        print(f"{key}: {averages[key]:.2f}")


if __name__ == "__main__":
    simulate_season_average()
