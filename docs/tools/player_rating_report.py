#!/usr/bin/env python3
"""Generate summary tables for hitter and pitcher ratings.

Usage::

    python docs/tools/player_rating_report.py \
        --players data/players.csv \
        --output docs/player_rating_report.md

The script reads the player CSV, splits hitters/pitchers, and writes a
markdown report with mean/min/max values plus 10-point histograms for
key ratings (contact/power/speed/discipline for hitters; velocity/
control/movement/endurance for pitchers).  Buckets make it easy to see
whether archetype coverage aligns with expectations.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


HITTER_METRICS = ("ch", "ph", "sp", "vl")
PITCHER_METRICS = ("fb", "control", "movement", "endurance")


def read_players(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    hitters: list[dict[str, str]] = []
    pitchers: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if not row:
                continue
            (pitchers if row.get("is_pitcher") == "1" else hitters).append(row)
    return hitters, pitchers


def bucketize(values: list[float]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for val in values:
        lower = int(val // 10 * 10)
        upper = lower + 9
        label = f"{lower:02d}-{upper:02d}"
        counts[label] += 1
    return sorted(counts.items(), key=lambda kv: kv[0])


def metric_stats(rows: list[dict[str, str]], metric: str) -> dict[str, float]:
    values = [float(row[metric]) for row in rows if row.get(metric)]
    if not values:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "hist": []}
    stats: dict[str, float | list[tuple[str, int]]] = {
        "mean": round(mean(values), 2),
        "min": min(values),
        "max": max(values),
        "hist": bucketize(values),
    }
    return stats


def archetype_counts(rows: list[dict[str, str]], group: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    if group == "hitters":
        for row in rows:
            ch = float(row.get("ch") or 0)
            ph = float(row.get("ph") or 0)
            if ch >= ph + 10:
                archetype = "contact"
            elif ph >= ch + 10:
                archetype = "power"
            else:
                archetype = "balanced"
            counts[archetype] += 1
    else:
        for row in rows:
            vel = float(row.get("fb") or row.get("arm") or 0)
            ctrl = float(row.get("control") or 0)
            if vel >= ctrl + 10:
                archetype = "power"
            elif ctrl >= vel + 10:
                archetype = "finesse"
            else:
                archetype = "balanced"
            role = row.get("preferred_pitching_role") or row.get("role") or ""
            if role:
                archetype = f"{archetype}:{role}"
            counts[archetype] += 1
    return dict(counts)


def write_section(
    fh,
    title: str,
    rows: list[dict[str, str]],
    metrics: tuple[str, ...],
) -> None:
    fh.write(f"## {title}\n\n")
    fh.write(f"Total players: **{len(rows)}**\n\n")
    for metric in metrics:
        stats = metric_stats(rows, metric)
        fh.write(f"### {metric.upper()}\n\n")
        fh.write(
            f"- Mean: **{stats['mean']}**  Min: {stats['min']}  Max: {stats['max']}\n\n"
        )
        fh.write("| Bucket | Count |\n|---|---:|\n")
        for bucket, count in stats["hist"]:
            fh.write(f"| {bucket} | {count} |\n")
        fh.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate player rating report.")
    parser.add_argument(
        "--players",
        type=Path,
        default=Path("data/players.csv"),
        help="Path to players CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/player_rating_report.md"),
        help="Output markdown file",
    )
    args = parser.parse_args()

    hitters, pitchers = read_players(args.players)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        fh.write("# Player Rating Report\n\n")
        fh.write(
            "Generated from `{}`. Buckets use 10-point spans to visualize\n".format(
                args.players
            )
        )
        fh.write("rating distribution coverage.\n\n")
        write_section(fh, "Hitters", hitters, HITTER_METRICS)
        hitter_arche = archetype_counts(hitters, "hitters")
        fh.write("### Hitter Archetype Split\n\n")
        fh.write("| Archetype | Count |\n|---|---:|\n")
        for key, count in sorted(hitter_arche.items(), key=lambda kv: kv[0]):
            fh.write(f"| {key} | {count} |\n")
        fh.write("\n")

        write_section(fh, "Pitchers", pitchers, PITCHER_METRICS)
        pitcher_arche = archetype_counts(pitchers, "pitchers")
        fh.write("### Pitcher Archetype Split (including roles when available)\n\n")
        fh.write("| Archetype | Count |\n|---|---:|\n")
        for key, count in sorted(pitcher_arche.items(), key=lambda kv: kv[0]):
            fh.write(f"| {key or 'unknown'} | {count} |\n")
        fh.write("\n")


if __name__ == "__main__":
    main()
