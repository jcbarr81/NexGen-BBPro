import csv
from pathlib import Path

from utils.path_utils import get_base_dir


def find_free_agents(players, roster_dir: str | Path = "data/rosters"):
    """Return a list of Player/Pitcher objects not assigned to any roster."""
    assigned_ids = set()

    roster_dir = Path(roster_dir)
    if not roster_dir.is_absolute():
        roster_dir = get_base_dir() / roster_dir

    for filename in roster_dir.iterdir():
        if filename.suffix == ".csv":
            with filename.open(mode="r", newline="") as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header if present
                for row in reader:
                    if row:
                        assigned_ids.add(row[0].strip())

    # Return only those players not assigned to any team
    return [p for p in players if p.player_id not in assigned_ids]
