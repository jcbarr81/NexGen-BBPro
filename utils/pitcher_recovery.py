from __future__ import annotations

from dataclasses import dataclass
import csv
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Dict, Iterable, Optional

from utils.path_utils import get_base_dir
from utils.pitcher_role import get_role
from utils.player_loader import load_players_from_csv
from utils.roster_loader import load_roster

_DATE_FORMAT = "%Y-%m-%d"
_EPOCH = date(1970, 1, 1)


def _resolve_path(path: str | Path) -> Path:
    base = get_base_dir()
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = base / resolved
    return resolved


def _parse_date(value: str | None) -> date:
    if not value:
        return _EPOCH
    try:
        return datetime.strptime(value, _DATE_FORMAT).date()
    except ValueError:
        return _EPOCH


def _format_date(value: date) -> str:
    return value.strftime(_DATE_FORMAT)


def _rest_days(pitches: int) -> int:
    if pitches <= 0:
        return 0
    if pitches <= 20:
        return 1
    if pitches <= 40:
        return 2
    if pitches <= 70:
        return 3
    if pitches <= 100:
        return 4
    return 5


@dataclass
class _PitcherStatus:
    available_on: str | None = None
    last_used: str | None = None
    last_pitches: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "available_on": self.available_on,
            "last_used": self.last_used,
            "last_pitches": self.last_pitches,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "_PitcherStatus":
        return cls(
            available_on=str(data.get("available_on"))
            if data.get("available_on")
            else None,
            last_used=str(data.get("last_used")) if data.get("last_used") else None,
            last_pitches=int(data.get("last_pitches", 0)),
        )


class PitcherRecoveryTracker:
    """Track pitcher rest and rotation assignments across the season."""

    _instance: "PitcherRecoveryTracker" | None = None

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = _resolve_path(path or "data/pitcher_recovery.json")
        self.data: Dict[str, Dict[str, object]] = {"teams": {}}
        self._assignments: Dict[str, str] = {}
        self._load()

    # ------------------------------------------------------------------
    @classmethod
    def instance(cls) -> "PitcherRecoveryTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    def _load(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (OSError, json.JSONDecodeError):
            loaded = {}
        teams = loaded.get("teams") if isinstance(loaded, dict) else None
        if isinstance(teams, dict):
            self.data["teams"] = teams
        else:
            self.data["teams"] = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"teams": self.data.get("teams", {})}
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    # ------------------------------------------------------------------
    def start_day(self, date_str: str) -> None:
        """Reset per-game assignments for *date_str*."""

        self._assignments.clear()
        self._current_date = date_str

    # ------------------------------------------------------------------
    def _ensure_team(
        self,
        team_id: str,
        players_file: str | Path,
        roster_dir: str | Path,
    ) -> Dict[str, object]:
        teams = self.data.setdefault("teams", {})
        entry = teams.get(team_id)
        resolved_players = str(_resolve_path(players_file))
        roster = load_roster(team_id, roster_dir)
        all_players = {
            player.player_id: player
            for player in load_players_from_csv(resolved_players)
        }
        active_pitchers = [
            all_players[pid]
            for pid in roster.act
            if pid in all_players and getattr(all_players[pid], "is_pitcher", False)
        ]
        pitcher_ids = [p.player_id for p in active_pitchers]

        saved_rotation = self._load_saved_rotation(team_id, roster_dir, pitcher_ids)

        if entry is None:
            entry = self._build_team_entry(active_pitchers, saved_rotation)
            teams[team_id] = entry
            self.save()
            return entry

        # Update rotation and pitcher list if the roster changed.
        entry_pitchers = entry.setdefault("pitchers", {})
        for pid in pitcher_ids:
            if pid not in entry_pitchers:
                entry_pitchers[pid] = _PitcherStatus().to_dict()
        # Remove pitchers no longer on the roster.
        for pid in list(entry_pitchers.keys()):
            if pid not in pitcher_ids:
                entry_pitchers.pop(pid, None)

        if saved_rotation:
            rotation = [pid for pid in saved_rotation if pid in pitcher_ids]
        else:
            rotation = entry.get("rotation") or []
            rotation = [pid for pid in rotation if pid in pitcher_ids]
            if len(rotation) < 5:
                extras = [pid for pid in pitcher_ids if pid not in rotation]
                rotation.extend(extras[: 5 - len(rotation)])
            if not rotation:
                rotation = self._build_rotation(active_pitchers)

        entry["rotation"] = rotation
        if rotation:
            entry["next_index"] = int(entry.get("next_index", 0) or 0) % len(rotation)
        else:
            entry["next_index"] = 0
        return entry

    # ------------------------------------------------------------------
    def _build_team_entry(self, pitchers: Iterable[object], saved_rotation: list[str] | None = None) -> Dict[str, object]:
        pitcher_list = list(pitchers)
        rotation = saved_rotation or self._build_rotation(pitcher_list)
        status = {
            getattr(p, "player_id"): _PitcherStatus().to_dict()
            for p in pitcher_list
        }
        return {
            "rotation": rotation,
            "next_index": 0,
            "pitchers": status,
        }

    def _load_saved_rotation(
        self,
        team_id: str,
        roster_dir: str | Path,
        valid_pitchers: list[str],
    ) -> list[str]:
        path = _resolve_path(roster_dir) / f"{team_id}_pitching.csv"
        if not path.exists():
            return []
        order_priority = {"SP1": 0, "SP2": 1, "SP3": 2, "SP4": 3, "SP5": 4}
        assignments: list[tuple[int, str]] = []
        seen: set[str] = set()
        try:
            with path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if len(row) < 2:
                        continue
                    pid = row[0].strip()
                    role = row[1].strip().upper()
                    order = order_priority.get(role)
                    if order is None or pid not in valid_pitchers or pid in seen:
                        continue
                    assignments.append((order, pid))
                    seen.add(pid)
        except OSError:
            return []
        assignments.sort(key=lambda item: item[0])
        return [pid for _, pid in assignments]

    def _build_rotation(self, pitchers: Iterable[object]) -> list[str]:
        starters: list[tuple[str, int]] = []
        relievers: list[tuple[str, int]] = []
        for pitcher in pitchers:
            role = get_role(pitcher)
            endurance = int(getattr(pitcher, "endurance", 0) or 0)
            pid = getattr(pitcher, "player_id", "")
            if not pid:
                continue
            if role == "SP":
                starters.append((pid, endurance))
            elif role == "RP":
                relievers.append((pid, endurance))
            else:
                # Treat unknowns as relievers to ensure inclusion.
                relievers.append((pid, endurance))
        starters.sort(key=lambda item: item[1], reverse=True)
        relievers.sort(key=lambda item: item[1], reverse=True)
        rotation = [pid for pid, _ in starters[:5]]
        for pid, _ in relievers:
            if len(rotation) >= 5:
                break
            if pid not in rotation:
                rotation.append(pid)
        if not rotation and relievers:
            rotation = [pid for pid, _ in relievers[:5]]
        return rotation


    # ------------------------------------------------------------------
    def ensure_team(
        self,
        team_id: str,
        players_file: str | Path,
        roster_dir: str | Path,
    ) -> None:
        # Ensure tracking exists for team even when starters are overridden.
        self._ensure_team(team_id, players_file, roster_dir)

    # ------------------------------------------------------------------
    def assign_starter(
        self,
        team_id: str,
        date_str: str,
        players_file: str | Path,
        roster_dir: str | Path,
    ) -> str | None:
        entry = self._ensure_team(team_id, players_file, roster_dir)
        rotation: list[str] = entry.get("rotation", []) or []
        if not rotation:
            return None
        next_index = int(entry.get("next_index", 0) or 0)
        pitchers = entry.get("pitchers", {})
        date_obj = _parse_date(date_str)
        chosen_index: Optional[int] = None
        total = len(rotation)
        for offset in range(total):
            idx = (next_index + offset) % total
            pid = rotation[idx]
            status = _PitcherStatus.from_dict(pitchers.get(pid, {}))
            if _parse_date(status.available_on) <= date_obj:
                chosen_index = idx
                break
        if chosen_index is None:
            # Everyone is tired; choose the least-rested pitcher.
            chosen_index = min(
                range(total),
                key=lambda idx: _parse_date(
                    _PitcherStatus.from_dict(pitchers.get(rotation[idx], {})).available_on
                ),
            )
        pid = rotation[chosen_index]
        entry["next_index"] = (chosen_index + 1) % total
        self._assignments[team_id] = pid
        self.save()
        return pid

    # ------------------------------------------------------------------
    def assigned_starter(self, team_id: str) -> str | None:
        return self._assignments.get(team_id)

    # ------------------------------------------------------------------
    def record_game(
        self,
        team_id: str,
        date_str: str,
        pitcher_stats: Iterable[object],
        players_file: str | Path,
        roster_dir: str | Path,
    ) -> None:
        entry = self._ensure_team(team_id, players_file, roster_dir)
        pitchers = entry.setdefault("pitchers", {})
        date_obj = _parse_date(date_str)
        updated = False
        for state in pitcher_stats:
            pitcher = getattr(state, "player", None)
            if pitcher is None:
                continue
            pid = getattr(pitcher, "player_id", None)
            if not pid:
                continue
            pitches = int(getattr(state, "pitches_thrown", 0) or 0)
            if pitches <= 0:
                continue
            rest_days = _rest_days(pitches)
            available_on = date_obj + timedelta(days=rest_days)
            status = _PitcherStatus.from_dict(pitchers.get(pid, {}))
            status.available_on = _format_date(available_on)
            status.last_used = date_str
            status.last_pitches = pitches
            pitchers[pid] = status.to_dict()
            updated = True
        if updated:
            self.save()


__all__ = ["PitcherRecoveryTracker"]


