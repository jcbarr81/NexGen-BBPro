"""League benchmark ingestion utilities.

The project contains a CSV of aggregated MLB statistics that serve as target
values for tuning the simulation. This module loads the file into a
``dict`` for convenient lookups.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import csv


BENCHMARK_CSV = Path("data/MLB_avg/mlb_league_benchmarks_2025_filled.csv")


@dataclass
class Benchmarks:
    """Container for league-wide benchmark metrics."""

    metrics: Dict[str, float]

    def __getitem__(self, key: str) -> float:
        return self.metrics[key]

    def league_average(self, key: str, default: float | None = None) -> float | None:
        """Return a league-average metric by ``key``."""
        return self.metrics.get(key, default)

    def park_factors(self) -> Dict[str, float]:
        """Return park factor metrics."""
        return {
            "overall": self.metrics.get("park_factor_overall", 100.0),
            "1b": self.metrics.get("park_factor_1b", 100.0),
            "2b": self.metrics.get("park_factor_2b", 100.0),
            "3b": self.metrics.get("park_factor_3b", 100.0),
            "hr": self.metrics.get("park_factor_hr", 100.0),
        }

    def weather_means(self) -> Dict[str, float]:
        """Return typical weather conditions used for tuning."""
        return {
            "temperature": self.metrics.get("weather_temp_mean", 70.0),
            "wind_speed": self.metrics.get("wind_speed_mean", 0.0),
        }


def load_benchmarks(path: str | Path = BENCHMARK_CSV) -> Benchmarks:
    """Load benchmark metrics from ``path`` into a :class:`Benchmarks` object."""

    path = Path(path)
    metrics: Dict[str, float] = {}
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                metrics[row["metric_key"]] = float(row["value"])
            except (KeyError, ValueError):
                continue
    return Benchmarks(metrics)


__all__ = ["Benchmarks", "load_benchmarks"]
