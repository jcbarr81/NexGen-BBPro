import csv
import hashlib
import json
import random
import warnings
from pathlib import Path
from functools import lru_cache
from typing import Dict, List

from models.roster import Roster
from utils.path_utils import get_base_dir
from .player_loader import load_players_from_csv

# Teams should field exactly 25 players on the active roster.
ACTIVE_ROSTER_SIZE = 25
_PLACEHOLDER_PLAYERS_FILE = "data/players.csv"
_PLACEHOLDER_HITTERS = 17
_PLACEHOLDER_PITCHERS = 8


def _placeholder_registry_path() -> Path:
    base = get_base_dir()
    return base / "data" / "rosters" / "_placeholder_registry.json"


class _PlaceholderPool:
    def __init__(self) -> None:
        self._hitter_pool: List = []
        self._pitcher_pool: List = []
        self._all_hitters: List = []
        self._all_pitchers: List = []
        self._assigned: Dict[str, str] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        players = load_players_from_csv(_PLACEHOLDER_PLAYERS_FILE)
        hitters = [
            p for p in players if not getattr(p, "is_pitcher", False)
        ]
        pitchers = [
            p for p in players if getattr(p, "is_pitcher", False)
        ]
        hitters_ordered = sorted(hitters, key=lambda p: getattr(p, "ch", 50))
        hitter_limit = max(_PLACEHOLDER_HITTERS, int(len(hitters_ordered) * 0.2))
        self._hitter_pool = hitters_ordered[:hitter_limit]
        self._all_hitters = hitters_ordered
        pitchers_ordered = sorted(
            pitchers,
            key=lambda p: getattr(p, "movement", 50) + getattr(p, "fb", 50),
            reverse=True,
        )
        pitcher_limit = max(_PLACEHOLDER_PITCHERS, int(len(pitchers_ordered) * 0.4))
        self._pitcher_pool = pitchers_ordered[:pitcher_limit]
        self._all_pitchers = pitchers_ordered
        self._assigned = self._load_registry()
        self._hydrate_from_rosters()
        self._loaded = True

    def _load_registry(self) -> Dict[str, str]:
        path = _placeholder_registry_path()
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        assignments: Dict[str, str] = {}
        for pid, team_id in data.items():
            if isinstance(pid, str) and isinstance(team_id, str):
                assignments[pid] = team_id
        return assignments

    def _save_registry(self) -> None:
        path = _placeholder_registry_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as fh:
                json.dump(self._assigned, fh, indent=2, sort_keys=True)
        except OSError:
            pass

    def _hydrate_from_rosters(self) -> None:
        roster_dir = get_base_dir() / "data" / "rosters"
        if not roster_dir.exists():
            return
        updated = False
        for path in sorted(roster_dir.glob("*.csv")):
            team_id = path.stem
            try:
                with path.open("r", encoding="utf-8", newline="") as fh:
                    reader = csv.reader(fh)
                    for row in reader:
                        if len(row) < 2:
                            continue
                        pid = row[0].strip()
                        if not pid:
                            continue
                        owner = self._assigned.get(pid)
                        if owner in (None, team_id):
                            if owner != team_id:
                                updated = True
                            self._assigned[pid] = team_id
            except OSError:
                continue
        if updated:
            self._save_registry()

    def _select_players(self, team_id: str, pool: List, count: int, salt: str) -> List:
        if not pool:
            return []

        rng = random.Random(_stable_seed(team_id, f"{salt}-placeholder"))
        ordered = list(pool)
        rng.shuffle(ordered)

        selected: List = []
        used_ids: set[str] = set()

        def _try_add(player) -> bool:
            pid = getattr(player, "player_id", None)
            if not pid or pid in used_ids:
                return False
            selected.append(player)
            used_ids.add(pid)
            return True

        for player in ordered:
            if self._assigned.get(player.player_id) == team_id:
                if len(selected) >= count:
                    break
                _try_add(player)
        if len(selected) < count:
            for player in ordered:
                if len(selected) >= count:
                    break
                owner = self._assigned.get(player.player_id)
                if owner in (None, team_id):
                    _try_add(player)
        if len(selected) < count:
            for player in ordered:
                if len(selected) >= count:
                    break
                _try_add(player)

        for player in selected:
            pid = getattr(player, "player_id", None)
            if pid:
                self._assigned[pid] = team_id
        return selected[:count]

    def assign_roster(self, team_id: str) -> tuple[List, List]:
        self._ensure_loaded()
        hitters = self._select_players(
            team_id,
            self._hitter_pool,
            _PLACEHOLDER_HITTERS,
            "hitters",
        )
        pitchers = self._select_players(
            team_id,
            self._pitcher_pool,
            _PLACEHOLDER_PITCHERS,
            "pitchers",
        )
        self._save_registry()
        return hitters, pitchers

    def record_roster(self, team_id: str, roster: Roster) -> None:
        self._ensure_loaded()
        changed = False
        for group in (roster.act, roster.aaa, roster.low, roster.dl, roster.ir):
            for pid in group:
                owner = self._assigned.get(pid)
                if owner in (None, team_id):
                    if owner != team_id:
                        changed = True
                    self._assigned[pid] = team_id
        if changed:
            self._save_registry()

    @property
    def all_hitters(self) -> List:
        self._ensure_loaded()
        return list(self._all_hitters)

    @property
    def all_pitchers(self) -> List:
        self._ensure_loaded()
        return list(self._all_pitchers)

    def reconcile_roster(self, team_id: str, roster: Roster) -> bool:
        """Remove players already assigned to a different team."""

        self._ensure_loaded()
        changed = False

        def _dedupe(group_name: str) -> None:
            nonlocal changed
            group = getattr(roster, group_name)
            unique: List[str] = []
            for pid in group:
                owner = self._assigned.get(pid)
                if owner is None:
                    self._assigned[pid] = team_id
                    unique.append(pid)
                    changed = True
                elif owner == team_id:
                    unique.append(pid)
                else:
                    if pid.startswith("D"):
                        changed = True
                        continue
                    unique.append(pid)
            if len(unique) != len(group):
                setattr(roster, group_name, unique)

        for name in ("act", "aaa", "low", "dl", "ir"):
            _dedupe(name)

        if changed:
            self._save_registry()
        return changed

    def acquire_placeholders(self, team_id: str, count: int) -> List[str]:
        """Return up to ``count`` unassigned placeholder player ids."""

        self._ensure_loaded()
        if count <= 0:
            return []
        additions: List[str] = []
        for pool in (self._hitter_pool, self._pitcher_pool):
            for player in pool:
                pid = getattr(player, "player_id", "")
                if not pid or self._assigned.get(pid):
                    continue
                self._assigned[pid] = team_id
                additions.append(pid)
                if len(additions) >= count:
                    self._save_registry()
                    return additions
        if additions:
            self._save_registry()
        return additions


_PLACEHOLDER_POOL: _PlaceholderPool | None = None


def _get_placeholder_pool() -> _PlaceholderPool:
    global _PLACEHOLDER_POOL
    if _PLACEHOLDER_POOL is None:
        _PLACEHOLDER_POOL = _PlaceholderPool()
    return _PLACEHOLDER_POOL


def _reset_placeholder_pool() -> None:
    global _PLACEHOLDER_POOL
    _PLACEHOLDER_POOL = None


def _stable_seed(team_id: str, salt: str) -> int:
    """Return a deterministic seed derived from ``team_id`` and ``salt``."""

    digest = hashlib.blake2s(
        f"{team_id}:{salt}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big")


def _generate_placeholder_roster(team_id: str) -> Roster:
    """Create a deterministic roster when no saved file exists for ``team_id``."""

    pool = _get_placeholder_pool()
    hitters, pitchers = pool.assign_roster(team_id)
    if len(hitters) < _PLACEHOLDER_HITTERS or len(pitchers) < _PLACEHOLDER_PITCHERS:
        raise FileNotFoundError("Insufficient player pool to build placeholder roster")

    selected_ids = {p.player_id for p in hitters + pitchers}

    act = [p.player_id for p in hitters + pitchers]
    remaining_hitters = [
        p.player_id
        for p in pool.all_hitters
        if p.player_id not in selected_ids
    ][:ACTIVE_ROSTER_SIZE]
    remaining_pitchers = [
        p.player_id
        for p in pool.all_pitchers
        if p.player_id not in selected_ids
    ][:ACTIVE_ROSTER_SIZE]

    roster = Roster(
        team_id=team_id,
        act=act,
        aaa=remaining_hitters,
        low=remaining_pitchers,
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
        _get_placeholder_pool().record_roster(team_id, roster)
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
    pool = _get_placeholder_pool()
    pool.reconcile_roster(team_id, roster)
    roster.promote_replacements(target_size=ACTIVE_ROSTER_SIZE)
    pool.reconcile_roster(team_id, roster)
    pool.record_roster(team_id, roster)
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


_original_cache_clear = getattr(load_roster, "cache_clear", None)


def _cache_clear_wrapper():
    _reset_placeholder_pool()
    if _original_cache_clear is not None:
        _original_cache_clear()


if _original_cache_clear is not None:
    load_roster.cache_clear = _cache_clear_wrapper  # type: ignore[attr-defined]
