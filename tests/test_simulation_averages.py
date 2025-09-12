import csv
import math
from datetime import timedelta
from pathlib import Path
import io
import contextlib

import scripts.simulate_season_avg as ssa
import playbalance.simulation as sim


def test_simulated_averages_close_to_mlb(monkeypatch):
    """Simulate a short season and compare averages to MLB benchmarks."""

    # Prevent stats from being written to disk during the test
    monkeypatch.setattr(sim, "save_stats", lambda players, teams: None)

    def short_schedule(teams, start_date):
        return [
            {
                "date": (start_date + timedelta(days=i)).isoformat(),
                "home": teams[0],
                "away": teams[1],
            }
            for i in range(10)
        ]

    # Use a deterministic short schedule to keep the test fast
    monkeypatch.setattr(ssa, "generate_mlb_schedule", short_schedule)

    # Capture printed averages from the simulation
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ssa.simulate_season_average(use_tqdm=False)
    lines = [
        line
        for line in buf.getvalue().splitlines()
        if ":" in line and line.split(":", 1)[0] in ssa.STAT_ORDER
    ]

    simulated = {}
    for line in lines:
        stat, rest = line.split(":", 1)
        parts = [p.strip() for p in rest.split(",")]
        sim_part = next(p for p in parts if p.startswith("Sim"))
        simulated[stat.strip()] = float(sim_part.split()[1])

    # Approximate at-bats using a 54-out baseline for both teams
    simulated["AtBats"] = simulated["Hits"] + 54

    # Load MLB benchmark averages from CSV
    csv_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "MLB_avg"
        / "mlb_avg_boxscore_2020_2024_both_teams.csv"
    )
    with csv_path.open(newline="") as f:
        row = next(csv.DictReader(f))
    benchmarks = {stat: float(value) for stat, value in row.items() if stat}

    # Assert simulated values are close to MLB averages
    for stat, mlb_val in benchmarks.items():
        sim_val = simulated[stat]
        assert math.isclose(sim_val, mlb_val, rel_tol=0.1), stat

    # Derived rate statistics using simple approximations
    hits = simulated["Hits"]
    doubles = simulated["Doubles"]
    triples = simulated["Triples"]
    homers = simulated["HomeRuns"]

    mlb_hits = benchmarks["Hits"]
    mlb_doubles = benchmarks["Doubles"]
    mlb_triples = benchmarks["Triples"]
    mlb_homers = benchmarks["HomeRuns"]

    ab = simulated["AtBats"]
    mlb_ab = benchmarks["AtBats"]
    singles = hits - doubles - triples - homers
    mlb_singles = mlb_hits - mlb_doubles - mlb_triples - mlb_homers
    total_bases = singles + 2 * doubles + 3 * triples + 4 * homers
    mlb_total_bases = mlb_singles + 2 * mlb_doubles + 3 * mlb_triples + 4 * mlb_homers

    ba = hits / ab if ab else 0.0
    mlb_ba = mlb_hits / mlb_ab if mlb_ab else 0.0
    slg = total_bases / ab if ab else 0.0
    mlb_slg = mlb_total_bases / mlb_ab if mlb_ab else 0.0
    hr_rate = homers / ab if ab else 0.0
    mlb_hr_rate = mlb_homers / mlb_ab if mlb_ab else 0.0

    for stat, sim_val, mlb_val in [
        ("BA", ba, mlb_ba),
        ("SLG", slg, mlb_slg),
        ("HR_rate", hr_rate, mlb_hr_rate),
    ]:
        assert math.isclose(sim_val, mlb_val, rel_tol=0.1), stat
