from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterable, Optional

from utils.path_utils import get_base_dir


def append_starter_hook_audit(
    entries: Iterable[str],
    *,
    game_date: Optional[str],
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
) -> None:
    """Persist starter hook audit entries to a CSV file when enabled.

    Controlled via the ``PB_STARTER_AUDIT_PATH`` environment variable. When
    unset, this function is a no-op.
    """

    path_token = os.getenv("PB_STARTER_AUDIT_PATH")
    if not path_token:
        return

    audit_path = Path(path_token)
    if not audit_path.is_absolute():
        audit_path = get_base_dir() / audit_path
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return

    headers = [
        "game",
        "team",
        "side",
        "inning",
        "half",
        "run_diff",
        "pid",
        "pitches",
        "endurance",
        "toast",
        "budget_remaining",
        "budget_pct",
        "max_budget",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
    ]

    file_exists = audit_path.exists()
    try:
        fh = audit_path.open("a", newline="", encoding="utf-8")
    except Exception:
        return

    with fh:
        writer = csv.writer(fh)
        if not file_exists:
            writer.writerow(headers)

        for entry in entries:
            if not entry.startswith("SP hook audit:"):
                continue
            payload = entry[len("SP hook audit:") :].strip().split()
            data: dict[str, str] = {}
            for token in payload:
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                data[key] = value

            def _parse_int(key: str) -> Optional[int]:
                value = data.get(key)
                if value is None or value.lower() == "n/a":
                    return None
                try:
                    return int(float(value))
                except ValueError:
                    return None

            def _parse_float(key: str) -> Optional[float]:
                value = data.get(key)
                if value is None or value.lower() == "n/a":
                    return None
                try:
                    return float(value)
                except ValueError:
                    return None

            row = [
                data.get("game") or (game_date or ""),
                data.get("team", ""),
                data.get("side", ""),
                _parse_int("inning"),
                data.get("half", ""),
                _parse_int("run_diff"),
                data.get("pid", ""),
                _parse_int("pitches"),
                _parse_int("endurance"),
                _parse_float("toast"),
                _parse_float("budget_remaining"),
                _parse_float("budget_pct"),
                _parse_float("max_budget"),
                home_team,
                away_team,
                home_score,
                away_score,
            ]
            writer.writerow(row)


__all__ = ["append_starter_hook_audit"]
