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


__all__ = ["load_benchmarks"]
