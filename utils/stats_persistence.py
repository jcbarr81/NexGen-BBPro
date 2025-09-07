"""Utilities for persisting season statistics.

Reads and writes to ``season_stats.json`` are guarded by an inter-process
file lock to prevent concurrent writers from corrupting the data.  On Unix
systems the lock is implemented with :mod:`fcntl`; on Windows it falls back
to :mod:`msvcrt`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

import contextlib
import errno
import os
import time

if os.name == "nt":  # pragma: no cover - Windows specific
    import msvcrt

    @contextlib.contextmanager
    def _locked(file):
        """Lock ``file`` using :mod:`msvcrt` semantics.

        ``msvcrt.locking`` cannot lock a file of zero length.  When the lock
        file is opened with ``"w"`` its size is truncated to ``0`` which would
        trigger ``OSError: [Errno 36]`` on Windows.  To avoid this we write a
        single byte before acquiring the lock.  The function also retries when
        the lock is temporarily unavailable, which can otherwise raise
        ``OSError: [Errno 36]`` (resource deadlock avoided).
        """
        # Ensure the file is at least one byte long before attempting to lock
        file.seek(0, os.SEEK_END)
        if file.tell() == 0:
            file.write("0")
            file.flush()
            file.seek(0)

        while True:
            try:
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError as exc:  # pragma: no cover - depends on timing
                if exc.errno not in (errno.EACCES, errno.EDEADLK):
                    raise
                time.sleep(0.01)

        try:
            yield
        finally:
            try:
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
else:  # Unix
    import fcntl

    @contextlib.contextmanager
    def _locked(file):
        """Lock ``file`` using :mod:`fcntl` semantics."""
        try:
            fcntl.flock(file, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)

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

    # ``"w"`` would truncate the file and prevent other processes from
    # opening it on Windows, leading to ``PermissionError`` when multiple
    # simulations attempt to write stats concurrently.  Using ``"a+"`` keeps
    # the file length intact and allows concurrent opens while the explicit
    # lock below serializes writes.
    with lock_path.open("a+") as lock_file:
        with _locked(lock_file):
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
