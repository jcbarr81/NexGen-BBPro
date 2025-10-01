from __future__ import annotations

from pathlib import Path
import csv
import json

from .path_utils import get_base_dir


def get_current_sim_date(base_dir: Path | None = None) -> str | None:
    """Return the current simulation date from schedule/progress, or None.

    Reads ``data/season_progress.json`` for ``sim_index`` and maps it to
    ``data/schedule.csv``. Values are clamped to valid ranges. If either file
    is missing or invalid, returns ``None``.
    """

    base = (base_dir or get_base_dir()) / "data"
    sched = base / "schedule.csv"
    prog = base / "season_progress.json"
    if not sched.exists() or not prog.exists():
        return None
    try:
        with prog.open("r", encoding="utf-8") as fh:
            progress = json.load(fh)
    except Exception:
        return None
    try:
        with sched.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:
        return None
    if not rows:
        return None
    # Build ordered list of unique dates as SeasonSimulator does
    unique_dates: list[str] = []
    seen: set[str] = set()
    for row in rows:
        date_val = str(row.get("date") or "").strip()
        if not date_val:
            continue
        if date_val not in seen:
            unique_dates.append(date_val)
            seen.add(date_val)
    if not unique_dates:
        return None
    try:
        sim_index = int(progress.get("sim_index", 0) or 0)
    except Exception:
        sim_index = 0
    sim_index = max(0, min(sim_index, len(unique_dates) - 1))
    return unique_dates[sim_index]
