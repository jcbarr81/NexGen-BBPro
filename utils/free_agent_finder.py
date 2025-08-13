import os
import csv

def find_free_agents(players, roster_dir="data/rosters"):
    """Return a list of Player/Pitcher objects not assigned to any roster."""
    assigned_ids = set()

    # Check all roster files and collect player_ids
    for filename in os.listdir(roster_dir):
        if filename.endswith(".csv"):
            with open(os.path.join(roster_dir, filename), mode="r", newline="") as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header if present
                for row in reader:
                    if row:
                        assigned_ids.add(row[0].strip())

    # Return only those players not assigned to any team
    return [p for p in players if p.player_id not in assigned_ids]
