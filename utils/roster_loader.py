import csv
import hashlib
import warnings
from pathlib import Path
from functools import lru_cache

from models.roster import Roster
from utils.path_utils import get_base_dir
from .player_loader import load_players_from_csv

# Teams should field exactly 25 players on the active roster.
ACTIVE_ROSTER_SIZE = 25
_PLACEHOLDER_PLAYERS_FILE = "data/players.csv"
_PLACEHOLDER_HITTERS = 17
_PLACEHOLDER_PITCHERS = 8


def _stable_seed(team_id: str, salt: str) -> int:
    """Return a deterministic seed derived from ``team_id`` and ``salt``."""

    digest = hashlib.blake2s(
        f"{team_id}:{salt}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big")


def _take_slice(players, count: int, seed: int) -> list:
    if count <= 0:
        return []
    if len(players) <= count:
        return list(players)
    max_offset = max(0, len(players) - count)
    offset = seed % (max_offset + 1) if max_offset else 0
    return list(players[offset : offset + count])


def _generate_placeholder_roster(team_id: str) -> Roster:
    """Create a deterministic roster when no saved file exists for ``team_id``."""

    players = load_players_from_csv(_PLACEHOLDER_PLAYERS_FILE)
    hitters = [p for p in players if not getattr(p, "is_pitcher", False)]
    pitchers = [p for p in players if getattr(p, "is_pitcher", False)]

    if len(hitters) < _PLACEHOLDER_HITTERS or len(pitchers) < _PLACEHOLDER_PITCHERS:
        raise FileNotFoundError("Insufficient player pool to build placeholder roster")

    hitters_ordered = sorted(hitters, key=lambda p: getattr(p, "ch", 50))
    hitter_pool = hitters_ordered[: max(_PLACEHOLDER_HITTERS, int(len(hitters_ordered) * 0.2))]
    selected_hitters = _take_slice(
        hitter_pool,
        _PLACEHOLDER_HITTERS,
        _stable_seed(team_id, "hitters"),
    )

    pitchers_ordered = sorted(
        pitchers,
        key=lambda p: getattr(p, "movement", 50) + getattr(p, "fb", 50),
        reverse=True,
    )
    pitcher_pool = pitchers_ordered[: max(_PLACEHOLDER_PITCHERS, int(len(pitchers_ordered) * 0.4))]
    selected_pitchers = _take_slice(
        pitcher_pool,
        _PLACEHOLDER_PITCHERS,
        _stable_seed(team_id, "pitchers"),
    )

    selected_ids = {
        *(p.player_id for p in selected_hitters),
        *(p.player_id for p in selected_pitchers),
    }

    act = [p.player_id for p in selected_hitters + selected_pitchers]
    remaining_hitters = [
        p.player_id for p in hitters if p.player_id not in selected_ids
    ]
    remaining_pitchers = [
        p.player_id for p in pitchers if p.player_id not in selected_ids
    ]

    roster = Roster(
        team_id=team_id,
        act=act,
        aaa=remaining_hitters[:ACTIVE_ROSTER_SIZE],
        low=remaining_pitchers[:ACTIVE_ROSTER_SIZE],
    )
    roster.promote_replacements(target_size=ACTIVE_ROSTER_SIZE)
    return roster


def _persist_placeholder_roster(file_path: Path, roster: Roster) -> None:
    """Write ``roster`` to ``file_path`` if possible."""

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open(mode="w", newline="") as fh:
            writer = csv.writer(fh)
            for player_id in roster.act:
                writer.writerow([player_id, "ACT"])
            for player_id in roster.aaa:
                writer.writerow([player_id, "AAA"])
            for player_id in roster.low:
                writer.writerow([player_id, "LOW"])
    except OSError as exc:
        warnings.warn(
            f"Unable to persist placeholder roster for {roster.team_id}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )


@lru_cache(maxsize=None)
def load_roster(team_id, roster_dir: str | Path = "data/rosters"):
    team_id = str(team_id)
    roster_dir = Path(str(roster_dir))
    act, aaa, low, dl, ir = [], [], [], [], []
    if not roster_dir.is_absolute():
        roster_dir = get_base_dir() / roster_dir
    file_path = roster_dir / f"{team_id}.csv"
    if not file_path.exists():
        roster = _generate_placeholder_roster(team_id)
        _persist_placeholder_roster(file_path, roster)
        return roster

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
    try:
        if filepath.exists():
            filepath.chmod(0o644)
    except Exception:
        pass
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
