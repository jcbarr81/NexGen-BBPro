import csv
from pathlib import Path

from models.roster import Roster
from utils.path_utils import get_base_dir
# Teams should field exactly 25 players on the active roster.
ACTIVE_ROSTER_SIZE = 25


def load_roster(team_id, roster_dir: str | Path = "data/rosters"):
    act, aaa, low, dl, ir = [], [], [], [], []
    roster_dir = Path(roster_dir)
    if not roster_dir.is_absolute():
        roster_dir = get_base_dir() / roster_dir
    file_path = roster_dir / f"{team_id}.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Roster file not found: {file_path}")

    with file_path.open(mode="r", newline="") as csvfile:
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
            elif level == "DL":
                dl.append(pid)
            elif level == "IR":
                ir.append(pid)

    roster = Roster(team_id=team_id, act=act, aaa=aaa, low=low, dl=dl, ir=ir)
    roster.promote_replacements(target_size=ACTIVE_ROSTER_SIZE)
    return roster


def save_roster(team_id, roster: Roster):
    filepath = get_base_dir() / "data" / "rosters" / f"{team_id}.csv"
    with filepath.open(mode="w", newline="") as f:
        writer = csv.writer(f)
        for level, group in [
            ("ACT", roster.act),
            ("AAA", roster.aaa),
            ("LOW", roster.low),
            ("DL", roster.dl),
            ("IR", roster.ir),
        ]:
            for player_id in group:
                writer.writerow([player_id, level])
