from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple

from .models import BatterRatings, PitcherRatings


def load_players(csv_path: Path) -> Tuple[List[BatterRatings], List[PitcherRatings]]:
    """Load players from ``players.csv`` and split into hitters/pitchers."""

    batters: List[BatterRatings] = []
    pitchers: List[PitcherRatings] = []
    with csv_path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            is_pitcher = str(row.get("is_pitcher", "0")).strip() in {"1", "True", "true", "yes"}
            if is_pitcher:
                pitchers.append(PitcherRatings.from_row(row))
            else:
                batters.append(BatterRatings.from_row(row))
    return batters, pitchers
