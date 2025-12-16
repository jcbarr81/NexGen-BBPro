#!/usr/bin/env python3
"""Normalize player ratings using shared archetype definitions.

This script rewrites ``data/players.csv`` (or a provided CSV) so that hitter
and pitcher ratings align with the archetype blueprint documented under
``docs/player_archetypes.md``.  Existing IDs/names/biographical data are
preserved; only the core ratings are resampled.

Usage examples::

    python scripts/normalize_players.py --players data/players.csv \
        --output data/players_normalized.csv

    # Overwrite the source file after review
    python scripts/normalize_players.py --players data/players.csv --in-place
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from typing import Dict

import sys
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from playbalance import archetypes


HITTER_FIELDS = ("ch", "ph", "sp", "vl")
PITCHER_FIELDS = ("control", "movement", "endurance", "hold_runner", "fb")


def _clamp(val: int, low: int = 30, high: int = 99) -> int:
    return max(low, min(high, val))


def normalize_hitter(row: Dict[str, str]) -> None:
    archetype_name = row.get("hitter_archetype") or archetypes.infer_hitter_archetype(row)
    ratings = archetypes.sample_hitter_ratings(archetype_name)
    row["hitter_archetype"] = ratings["archetype"]
    contact = ratings["contact"]
    power = ratings["power"]
    speed = ratings["speed"]
    discipline = ratings["discipline"]
    row["ch"] = str(_clamp(contact))
    row["ph"] = str(_clamp(power))
    row["sp"] = str(_clamp(speed))
    row["vl"] = str(_clamp(discipline))


def normalize_pitcher(row: Dict[str, str]) -> None:
    archetype_name = row.get("pitcher_archetype") or row.get("preferred_pitching_role")
    archetype_name = archetype_name.lower() if archetype_name else None
    ratings = archetypes.sample_pitcher_core(archetype_name)
    row["pitcher_archetype"] = ratings["archetype"]
    row["control"] = str(_clamp(int(ratings["control"])))
    row["movement"] = str(_clamp(int(ratings["movement"])))
    row["endurance"] = str(_clamp(int(ratings["endurance"])))
    row["hold_runner"] = str(_clamp(int(ratings["hold_runner"])))
    row["fb"] = str(_clamp(int(ratings["velocity"])))
    if ratings.get("preferred_role"):
        row["preferred_pitching_role"] = ratings["preferred_role"]


def normalize(players_path: Path, output_path: Path) -> None:
    with players_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        rows = list(reader)

    fieldnames = reader.fieldnames or []
    for row in rows:
        if row.get("is_pitcher") == "1":
            normalize_pitcher(row)
        else:
            normalize_hitter(row)
        # Track any new fields added during normalization (e.g., archetype tags)
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    if not fieldnames:
        fieldnames = sorted({k for row in rows for k in row})
    with output_path.open("w", newline="", encoding="utf-8") as dest:
        writer = csv.DictWriter(dest, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--players",
        type=Path,
        default=Path("data/players.csv"),
        help="Input players CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. When omitted use --in-place.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducibility",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file instead of writing a new one",
    )
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    if args.output is None and not args.in_place:
        parser.error("Specify --output or --in-place")

    output_path = args.players if args.in_place else args.output
    assert output_path is not None
    normalize(args.players, output_path)
    print(f"Normalized players written to {output_path}")


if __name__ == "__main__":
    main()
