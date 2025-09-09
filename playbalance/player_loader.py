"""Utilities for loading player ratings from CSV data."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping
import csv

from .ratings import clamp_rating


@dataclass
class Player:
    """Lightweight representation of a player with mapped ratings."""

    player_id: str
    name: str
    is_pitcher: bool
    ratings: Dict[str, float]


def _to_rating(value: str | float) -> float:
    """Convert ``value`` to a 0-100 rating."""

    try:
        return clamp_rating(float(value))
    except (TypeError, ValueError):
        return 50.0


def load_players(path: str | Path) -> Dict[str, Player]:
    """Load players from ``path`` returning a mapping by ``player_id``.

    The CSV is expected to contain the fields used by the internal play-balance
    schema.  Pitching ratings map ``fb`` and ``sl`` to ``fastball`` and
    ``slider`` respectively along with ``control`` and ``movement``.  Batting
    ratings map ``ch`` to ``contact`` and ``pl`` to ``discipline``.
    """

    path = Path(path)
    players: Dict[str, Player] = {}
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pid = row.get("player_id")
            if not pid:
                continue
            is_pitcher = row.get("is_pitcher", "0") == "1"
            name = f"{row.get('first_name','')} {row.get('last_name','')}".strip()
            ratings: Dict[str, float] = {}
            if is_pitcher:
                ratings["fastball"] = _to_rating(row.get("fb", 50))
                ratings["slider"] = _to_rating(row.get("sl", 50))
                ratings["control"] = _to_rating(row.get("control", 50))
                ratings["movement"] = _to_rating(row.get("movement", 50))
            else:
                ratings["contact"] = _to_rating(row.get("ch", 50))
                ratings["discipline"] = _to_rating(row.get("pl", 50))
            players[pid] = Player(pid, name, is_pitcher, ratings)
    return players


def load_lineup(path: str | Path, players: Mapping[str, Player]) -> list[Player]:
    """Return batting order from ``path`` using ``players`` mapping."""

    path = Path(path)
    lineup: list[Player] = []
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pid = row.get("player_id")
            if pid and pid in players:
                lineup.append(players[pid])
    return lineup


def load_pitching_staff(path: str | Path, players: Mapping[str, Player]) -> list[Player]:
    """Return pitching staff from roster ``path`` using ``players`` mapping."""

    path = Path(path)
    staff: list[Player] = []
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            pid = row[0]
            if pid in players and players[pid].is_pitcher:
                staff.append(players[pid])
    return staff


__all__ = ["Player", "load_players", "load_lineup", "load_pitching_staff"]
