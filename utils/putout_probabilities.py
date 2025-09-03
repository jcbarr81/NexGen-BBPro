"""Utility functions for computing MLB putout probabilities by position."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict


def load_putout_probabilities(path: Path) -> Dict[str, float]:
    """Return per-position putout probabilities derived from ``path``.

    The CSV file must contain ``POS`` and ``avg_PO_per_game`` columns. The
    values are normalised so the returned probabilities sum to ``1``.
    """

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        avgs = {row["POS"].upper(): float(row["avg_PO_per_game"]) for row in reader}
    total = sum(avgs.values()) or 1.0
    return {pos: val / total for pos, val in avgs.items()}
