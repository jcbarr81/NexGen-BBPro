from __future__ import annotations

"""Merge per-day season history shards into the canonical stats file.

Usage (PowerShell):
  python scripts/merge_season_history.py

Optional env vars:
  - PB_STATS_PATH: override canonical path (default data/season_stats.json)
  - PB_HISTORY_DIR: override shards dir (default data/season_history)
"""

import os
from pathlib import Path

from utils.stats_persistence import merge_daily_history


def main() -> None:
    path = os.getenv("PB_STATS_PATH", "data/season_stats.json")
    shards = os.getenv("PB_HISTORY_DIR", "data/season_history")
    out = merge_daily_history(path=path, shards_dir=shards)
    print(f"Merged daily history into {Path(out).as_posix()}")


if __name__ == "__main__":
    main()

