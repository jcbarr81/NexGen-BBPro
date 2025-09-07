"""Utilities for persisting season statistics.

Reads and writes to ``season_stats.json`` are guarded by an inter-process
file lock (via :mod:`fcntl`) to prevent concurrent writers from corrupting
the data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

import fcntl

from utils.path_utils import get_base_dir


def _resolve_path(path: str | Path) -> Path:
    base_dir = get_base_dir()
    p = Path(path)
    if not p.is_absolute():
        p = base_dir / p
    return p


def load_stats(path: str | Path = "data/season_stats.json") -> Dict[str, Any]:
    file_path = _resolve_path(path)
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    return {
        "players": data.get("players", {}),
        "teams": data.get("teams", {}),
        "history": data.get("history", []),
    }


def save_stats(
    players: Iterable[Any],
    teams: Iterable[Any],
    path: str | Path = "data/season_stats.json",
) -> None:
    """Persist season statistics with an inter-process file lock."""

    file_path = _resolve_path(path)
    lock_path = file_path.with_suffix(file_path.suffix + ".lock")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        stats = load_stats(file_path)
        player_stats = stats.get("players", {})
        for player in players:
            season = getattr(player, "season_stats", None)
            if season:
                player_stats[player.player_id] = season
        team_stats = stats.get("teams", {})
        for team in teams:
            season = getattr(team, "season_stats", None)
            if season:
                team_stats[team.team_id] = season
        history = stats.get("history", [])
        history.append(
            {
                "players": {
                    p.player_id: getattr(p, "season_stats", {}) for p in players
                },
                "teams": {t.team_id: getattr(t, "season_stats", {}) for t in teams},
            }
        )
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "players": player_stats,
                    "teams": team_stats,
                    "history": history,
                },
                f,
                indent=2,
            )
