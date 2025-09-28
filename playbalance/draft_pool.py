from __future__ import annotations

"""Draft pool generation and I/O helpers (initial scaffold).

This module provides a minimal, deterministic draft pool generator so we can
exercise Draft Day pause/resume. It favors simplicity: names are sampled from
``data/names.csv`` (or ``data/players.csv`` if present), positions are
distributed across P/C/IF/OF buckets, and ratings are basic placeholders.

The file formats are intentionally simple and will evolve as the draft console
gains features:

- CSV: data/draft_pool_<year>.csv
- JSON: data/draft_pool_<year>.json (simple list of dicts)
"""

import csv
import json
import random
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List

from utils.path_utils import get_base_dir


BASE = get_base_dir()
NAMES = BASE / "data" / "names.csv"
PLAYERS = BASE / "data" / "players.csv"


@dataclass
class DraftProspect:
    player_id: str
    first_name: str
    last_name: str
    bats: str
    throws: str
    primary_position: str
    other_positions: List[str]
    is_pitcher: bool
    birthdate: str
    ch: int = 50
    ph: int = 50
    sp: int = 50
    fa: int = 50
    arm: int = 50
    endurance: int = 0
    control: int = 0
    movement: int = 0
    hold_runner: int = 0


def _name_source() -> List[Dict[str, str]]:
    path = PLAYERS if PLAYERS.exists() else NAMES
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _id_gen(year: int) -> Iterable[str]:
    n = 1
    while True:
        yield f"D{year}{n:04d}"
        n += 1


def _pick_position() -> str:
    # Rough distribution: 45% P, 10% C, 30% IF, 15% OF
    r = random.random()
    if r < 0.45:
        return "P"
    if r < 0.55:
        return "C"
    if r < 0.85:
        return random.choice(["1B", "2B", "3B", "SS"])
    return random.choice(["LF", "CF", "RF"])


def generate_draft_pool(year: int, *, size: int = 200, seed: int | None = None) -> List[DraftProspect]:
    rng = random.Random(seed)
    rows = _name_source()
    if not rows:
        rows = [{"first_name": "Prospect", "last_name": f"{i}"} for i in range(size)]

    ids = _id_gen(year)
    pool: List[DraftProspect] = []
    for _ in range(size):
        row = rng.choice(rows)
        first = row.get("first_name", "Prospect")
        last = row.get("last_name", "Unknown")
        pos = _pick_position()
        is_pitcher = pos == "P"
        bats = rng.choice(["R", "L", "S"])
        throws = rng.choice(["R", "L"]) if is_pitcher else bats
        birthdate = f"{year-18}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
        if is_pitcher:
            endurance = rng.randint(40, 80)
            control = rng.randint(35, 70)
            movement = rng.randint(35, 70)
            hold = rng.randint(30, 60)
        else:
            endurance = control = movement = hold = 0
        ch = rng.randint(35, 70)
        ph = rng.randint(35, 70)
        sp = rng.randint(30, 75)
        fa = rng.randint(30, 75)
        arm = rng.randint(30, 75)
        pool.append(
            DraftProspect(
                player_id=next(ids),
                first_name=first,
                last_name=last,
                bats=bats,
                throws=throws,
                primary_position=pos,
                other_positions=[],
                is_pitcher=is_pitcher,
                birthdate=birthdate,
                ch=ch,
                ph=ph,
                sp=sp,
                fa=fa,
                arm=arm,
                endurance=endurance,
                control=control,
                movement=movement,
                hold_runner=hold,
            )
        )
    return pool


def save_draft_pool(year: int, prospects: List[DraftProspect]) -> None:
    base = BASE / "data"
    base.mkdir(parents=True, exist_ok=True)
    csv_path = base / f"draft_pool_{year}.csv"
    json_path = base / f"draft_pool_{year}.json"
    def _write_files():
        # CSV
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            fieldnames = list(asdict(prospects[0]).keys()) if prospects else [
                "player_id",
                "first_name",
                "last_name",
                "bats",
                "throws",
                "primary_position",
                "other_positions",
                "is_pitcher",
                "birthdate",
            ]
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for p in prospects:
                writer.writerow(asdict(p))
        # JSON
        with json_path.open("w", encoding="utf-8") as fh:
            json.dump([asdict(p) for p in prospects], fh, indent=2)
    _with_lock(json_path.with_suffix(json_path.suffix + ".lock"), _write_files)


def load_draft_pool(year: int) -> List[Dict[str, object]]:
    json_path = BASE / "data" / f"draft_pool_{year}.json"
    if not json_path.exists():
        return []
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return []


__all__ = [
    "DraftProspect",
    "generate_draft_pool",
    "save_draft_pool",
    "load_draft_pool",
]


def _with_lock(lock_path: Path, action) -> None:
    for _ in range(200):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            try:
                action()
            finally:
                os.close(fd)
                try:
                    os.remove(str(lock_path))
                except OSError:
                    pass
            return
        except FileExistsError:
            time.sleep(0.05)
    action()
