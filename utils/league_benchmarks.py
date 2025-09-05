"""Utilities for loading MLB league benchmark metrics."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict


def load_league_benchmarks(path: Path) -> Dict[str, float]:
    """Return a mapping of league benchmark metrics from ``path``.

    The CSV at ``path`` must contain ``metric_key`` and ``value`` columns.
    Values are returned as floats keyed by the metric name.
    """

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return {row["metric_key"]: float(row["value"]) for row in reader}
