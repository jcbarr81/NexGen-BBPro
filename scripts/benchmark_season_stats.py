#!/usr/bin/env python3
"""Compare season stats against MLB benchmark metrics."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict


def _load_benchmarks(path: Path) -> Dict[str, float]:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        metrics: Dict[str, float] = {}
        for row in reader:
            key = (row.get("metric_key") or "").strip()
            if not key:
                continue
            raw = row.get("value")
            if raw in (None, ""):
                continue
            try:
                metrics[key] = float(raw)
            except ValueError:
                continue
    return metrics


def _as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _rate(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _aggregate_season_stats(path: Path) -> Dict[str, Dict[str, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    players = payload.get("players", {}) or {}

    batting_totals = {
        "pa": 0.0,
        "ab": 0.0,
        "h": 0.0,
        "b1": 0.0,
        "b2": 0.0,
        "b3": 0.0,
        "hr": 0.0,
        "bb": 0.0,
        "ibb": 0.0,
        "hbp": 0.0,
        "sf": 0.0,
        "sh": 0.0,
        "so": 0.0,
        "sb": 0.0,
        "cs": 0.0,
        "pitches": 0.0,
        "gb": 0.0,
        "ld": 0.0,
        "fb": 0.0,
    }
    pitching_totals = {
        "bf": 0.0,
        "outs": 0.0,
        "h": 0.0,
        "hr": 0.0,
        "bb": 0.0,
        "so": 0.0,
        "pitches_thrown": 0.0,
        "balls_thrown": 0.0,
        "strikes_thrown": 0.0,
        "first_pitch_strikes": 0.0,
        "zone_pitches": 0.0,
        "o_zone_pitches": 0.0,
        "zone_swings": 0.0,
        "o_zone_swings": 0.0,
        "zone_contacts": 0.0,
        "o_zone_contacts": 0.0,
        "so_looking": 0.0,
        "so_swinging": 0.0,
        "gb": 0.0,
        "ld": 0.0,
        "fb": 0.0,
    }

    for stats in players.values():
        if stats.get("pa") is not None:
            for key in batting_totals:
                batting_totals[key] += _as_float(stats.get(key))
        if stats.get("bf") is not None or stats.get("outs") is not None:
            for key in pitching_totals:
                pitching_totals[key] += _as_float(stats.get(key))

    return {"batting": batting_totals, "pitching": pitching_totals}


def _compute_metrics(totals: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    bat = totals["batting"]
    pit = totals["pitching"]

    pa = bat["pa"]
    ab = bat["ab"]
    h = bat["h"]
    hr = bat["hr"]
    so = bat["so"]
    bb = bat["bb"]
    hbp = bat["hbp"]
    sf = bat["sf"]
    b1 = bat["b1"]
    b2 = bat["b2"]
    b3 = bat["b3"]
    tb = b1 + 2 * b2 + 3 * b3 + 4 * hr

    bip = bat["gb"] + bat["ld"] + bat["fb"]
    pitches = bat["pitches"]

    swings = pit["zone_swings"] + pit["o_zone_swings"]
    contacts = pit["zone_contacts"] + pit["o_zone_contacts"]
    zone_pitches = pit["zone_pitches"]
    o_zone_pitches = pit["o_zone_pitches"]

    metrics = {
        "pitches_per_pa": _rate(pitches, pa),
        "avg": _rate(h, ab),
        "obp": _rate(h + bb + hbp, ab + bb + hbp + sf),
        "slg": _rate(tb, ab),
        "ops": _rate(h + bb + hbp, ab + bb + hbp + sf) + _rate(tb, ab),
        "iso": _rate(tb, ab) - _rate(h, ab),
        "babip": _rate(h - hr, ab - so - hr + sf),
        "k_pct": _rate(so, pa),
        "bb_pct": _rate(bb, pa),
        "k_minus_bb_pct": _rate(so - bb, pa),
        "swing_pct": _rate(swings, zone_pitches + o_zone_pitches),
        "z_swing_pct": _rate(pit["zone_swings"], zone_pitches),
        "o_swing_pct": _rate(pit["o_zone_swings"], o_zone_pitches),
        "contact_pct": _rate(contacts, swings),
        "z_contact_pct": _rate(pit["zone_contacts"], pit["zone_swings"]),
        "o_contact_pct": _rate(pit["o_zone_contacts"], pit["o_zone_swings"]),
        "first_pitch_strike_pct": _rate(pit["first_pitch_strikes"], pit["bf"]),
        "zone_pct": _rate(zone_pitches, zone_pitches + o_zone_pitches),
        "pitches_put_in_play_pct": _rate(bip, pitches),
        "bip_gb_pct": _rate(bat["gb"], bip),
        "bip_ld_pct": _rate(bat["ld"], bip),
        "bip_fb_pct": _rate(bat["fb"], bip),
        "hr_per_fb_pct": _rate(hr, bat["fb"] + hr),
        "sb_pct": _rate(bat["sb"], bat["sb"] + bat["cs"]),
        "sba_per_pa": _rate(bat["sb"] + bat["cs"], pa),
        "called_third_strike_share_of_so": _rate(
            pit["so_looking"], pit["so_looking"] + pit["so_swinging"]
        ),
    }
    return metrics


def _format_rows(metrics: Dict[str, float], benchmarks: Dict[str, float]) -> list[tuple[str, float, float, float]]:
    rows: list[tuple[str, float, float, float]] = []
    for key, mlb in benchmarks.items():
        if key not in metrics:
            continue
        sim = metrics[key]
        rows.append((key, sim, mlb, sim - mlb))
    rows.sort(key=lambda r: abs(r[3]), reverse=True)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--season-stats",
        type=Path,
        default=Path("data/season_stats.json"),
        help="Season stats JSON file",
    )
    parser.add_argument(
        "--benchmarks",
        type=Path,
        default=Path("data/MLB_avg/mlb_league_benchmarks_2025_filled.csv"),
        help="Benchmark CSV file",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Number of rows to display (sorted by absolute delta)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path to write a JSON report",
    )
    args = parser.parse_args()

    if not args.season_stats.exists():
        raise FileNotFoundError(f"Season stats file not found: {args.season_stats}")

    benchmarks = _load_benchmarks(args.benchmarks)
    totals = _aggregate_season_stats(args.season_stats)
    metrics = _compute_metrics(totals)
    rows = _format_rows(metrics, benchmarks)

    print(f"Season stats: {args.season_stats}")
    print(f"Benchmark file: {args.benchmarks}")
    print("Metrics vs MLB (sorted by abs delta):")
    for key, sim, mlb, delta in rows[: max(args.top, 0)]:
        print(f"{key:32s} sim={sim:.3f} mlb={mlb:.3f} delta={delta:+.3f}")

    missing = sorted(key for key in benchmarks.keys() if key not in metrics)
    if missing:
        print("\nBenchmarks not computed from season_stats:")
        for key in missing:
            print(f"  - {key}")

    if args.json:
        report = {
            "season_stats": str(args.season_stats),
            "benchmarks": str(args.benchmarks),
            "metrics": metrics,
            "rows": [
                {"metric_key": key, "sim": sim, "mlb": mlb, "delta": delta}
                for key, sim, mlb, delta in rows
            ],
            "missing": missing,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote JSON report to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
