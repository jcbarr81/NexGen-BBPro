import csv
import os
from models.roster import Roster

def load_roster(team_id, roster_dir="data/rosters"):
    act, aaa, low = [], [], []
    file_path = os.path.join(roster_dir, f"{team_id}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Roster file not found: {file_path}")

    with open(file_path, mode="r", newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) < 2:
                continue  # skip malformed rows
            pid = row[0].strip()
            level = row[1].strip().upper()
            if level == "ACT":
                act.append(pid)
            elif level == "AAA":
                aaa.append(pid)
            elif level == "LOW":
                low.append(pid)

    return Roster(team_id=team_id, act=act, aaa=aaa, low=low)

def save_roster(team_id, roster: Roster):
    filepath = os.path.join("data", "rosters", f"{team_id}.csv")
    with open(filepath, mode="w", newline="") as f:
        writer = csv.writer(f)
        for level, group in [("ACT", roster.act), ("AAA", roster.aaa), ("LOW", roster.low)]:
            for player_id in group:
                writer.writerow([player_id, level])
