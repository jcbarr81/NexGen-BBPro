"""League benchmark ingestion utilities.

The project contains a CSV of aggregated MLB statistics that serve as target
values for tuning the simulation. This module loads the file into a
``dict`` for convenient lookups.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict
import csv


BENCHMARK_CSV = Path("data/MLB_avg/mlb_league_benchmarks_2025_filled.csv")


def load_benchmarks(path: str | Path = BENCHMARK_CSV) -> Dict[str, float]:
    """Load benchmark metrics from ``path``.

    Parameters
    ----------
    path:
        CSV file with two columns: ``metric_key`` and ``value``.
    """
    path = Path(path)
    benchmarks: Dict[str, float] = {}
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                benchmarks[row["metric_key"]] = float(row["value"])
            except (KeyError, ValueError):
                continue
    return benchmarks


def park_factors(benchmarks: Dict[str, float]) -> Dict[str, float]:
    """Extract park factor metrics from ``benchmarks``.

    Parameters
    ----------
    benchmarks:
        Mapping of metric keys to values as returned by :func:`load_benchmarks`.
    """

    return {
        "overall": benchmarks.get("park_factor_overall", 100.0),
        "1b": benchmarks.get("park_factor_1b", 100.0),
        "2b": benchmarks.get("park_factor_2b", 100.0),
        "3b": benchmarks.get("park_factor_3b", 100.0),
        "hr": benchmarks.get("park_factor_hr", 100.0),
    }


def weather_profile(benchmarks: Dict[str, float]) -> Dict[str, float]:
    """Return typical weather conditions from the benchmark data."""

    return {
        "temperature": benchmarks.get("weather_temp_mean", 72.0),
        "wind_speed": benchmarks.get("wind_speed_mean", 0.0),
    }


def league_averages(benchmarks: Dict[str, float]) -> Dict[str, float]:
    """Return only metrics prefixed with ``avg_`` from ``benchmarks``."""

    return {k[4:]: v for k, v in benchmarks.items() if k.startswith("avg_")}


__all__ = [
    "load_benchmarks",
    "park_factors",
    "weather_profile",
    "league_averages",
]
