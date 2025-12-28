from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Tuple


def _parse_float(value: str) -> float:
    value = (value or "").strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


@dataclass
class ParkAgg:
    weight: float = 0.0
    sums: Dict[str, float] = field(default_factory=dict)
    years: set[int] = field(default_factory=set)

    def add(self, component: str, value: float, weight: float) -> None:
        self.sums[component] = self.sums.get(component, 0.0) + value * weight


def _load_visitor_stats(path: Path) -> Dict[Tuple[int, str], Dict[str, float]]:
    stats: Dict[Tuple[int, str], Dict[str, float]] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                year = int(row.get("Year") or 0)
            except ValueError:
                continue
            team_id = (row.get("TeamID") or "").strip()
            if not year or not team_id:
                continue
            r = _parse_float(row.get("R_Off_A")) + _parse_float(row.get("R_Def_A"))
            hr = _parse_float(row.get("HR_Off_A")) + _parse_float(row.get("HR_Def_A"))
            h = _parse_float(row.get("H_Off_A")) + _parse_float(row.get("H_Def_A"))
            d = _parse_float(row.get("D_Off_A")) + _parse_float(row.get("D_Def_A"))
            t = _parse_float(row.get("T_Off_A")) + _parse_float(row.get("T_Def_A"))
            ab = _parse_float(row.get("AB_Off_A")) + _parse_float(row.get("AB_Def_A"))
            singles = max(0.0, h - d - t - hr)
            stats[(year, team_id)] = {
                "r": r,
                "hr": hr,
                "h": h,
                "1b": singles,
                "2b": d,
                "3b": t,
                "ab": ab,
            }
    return stats


def _load_latest_park_names(path: Path) -> Dict[str, str]:
    latest: Dict[str, Tuple[int, str]] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            park_id = (row.get("parkID") or row.get("ParkID") or "").strip()
            name = (row.get("NAME") or row.get("Name") or "").strip()
            if not park_id or not name:
                continue
            try:
                year = int(row.get("Year") or 0)
            except ValueError:
                continue
            current = latest.get(park_id)
            if current is None or year > current[0]:
                latest[park_id] = (year, name)
    return {park_id: info[1] for park_id, info in latest.items()}


def _year_bounds(path: Path) -> Tuple[int, int]:
    min_year = 9999
    max_year = 0
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                year = int(row.get("Year") or 0)
            except ValueError:
                continue
            if year:
                min_year = min(min_year, year)
                max_year = max(max_year, year)
    if max_year == 0:
        return 0, 0
    if min_year == 9999:
        min_year = max_year
    return min_year, max_year


def compute_factors(
    home_path: Path,
    visitor_stats: Dict[Tuple[int, str], Dict[str, float]],
    start_year: int,
    end_year: int,
) -> Dict[str, ParkAgg]:
    agg: Dict[str, ParkAgg] = defaultdict(ParkAgg)
    with home_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                year = int(row.get("Year") or 0)
            except ValueError:
                continue
            if not year or year < start_year or year > end_year:
                continue
            team_id = (row.get("TeamID") or "").strip()
            park_id = (row.get("Park_ID") or row.get("ParkID") or "").strip()
            if not team_id or not park_id:
                continue
            road = visitor_stats.get((year, team_id))
            if not road:
                continue
            home_r = _parse_float(row.get("R_Off_H")) + _parse_float(row.get("R_Def_H"))
            home_hr = _parse_float(row.get("HR_Off_H")) + _parse_float(row.get("HR_Def_H"))
            home_h = _parse_float(row.get("H_Off_H")) + _parse_float(row.get("H_Def_H"))
            home_d = _parse_float(row.get("D_Off_H")) + _parse_float(row.get("D_Def_H"))
            home_t = _parse_float(row.get("T_Off_H")) + _parse_float(row.get("T_Def_H"))
            home_ab = _parse_float(row.get("AB_Off_H")) + _parse_float(row.get("AB_Def_H"))
            if home_ab <= 0:
                continue
            road_ab = road.get("ab", 0.0)
            if road_ab <= 0:
                continue
            home_1b = max(0.0, home_h - home_d - home_t - home_hr)
            components = {
                "r": home_r,
                "hr": home_hr,
                "h": home_h,
                "1b": home_1b,
                "2b": home_d,
                "3b": home_t,
            }
            for key, home_val in components.items():
                road_val = road.get(key, 0.0)
                if road_val <= 0:
                    continue
                home_rate = home_val / home_ab
                road_rate = road_val / road_ab
                if road_rate <= 0:
                    continue
                factor = home_rate / road_rate
                agg_entry = agg[park_id]
                agg_entry.add(key, factor, home_ab)
                agg_entry.years.add(year)
            agg[park_id].weight += home_ab
    return agg


def _format_factor(value: float) -> str:
    return f"{value * 100.0:.1f}"


def _write_factors(
    output_path: Path,
    park_names: Dict[str, str],
    aggs: Dict[str, ParkAgg],
    start_year: int,
    end_year: int,
) -> None:
    rows = []
    for park_id, data in aggs.items():
        if data.weight <= 0:
            continue
        name = park_names.get(park_id)
        if not name:
            continue
        factors = {key: data.sums[key] / data.weight for key in data.sums}
        rows.append(
            {
                "ParkID": park_id,
                "Venue": name,
                "StartYear": min(data.years) if data.years else start_year,
                "EndYear": max(data.years) if data.years else end_year,
                "Park Factor": _format_factor(factors.get("hr", 1.0)),
                "Run Factor": _format_factor(factors.get("r", 1.0)),
                "HR Factor": _format_factor(factors.get("hr", 1.0)),
                "1B Factor": _format_factor(factors.get("1b", 1.0)),
                "2B Factor": _format_factor(factors.get("2b", 1.0)),
                "3B Factor": _format_factor(factors.get("3b", 1.0)),
                "H Factor": _format_factor(factors.get("h", 1.0)),
            }
        )
    rows.sort(key=lambda row: row["Venue"].lower())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "ParkID",
            "Venue",
            "StartYear",
            "EndYear",
            "Park Factor",
            "Run Factor",
            "HR Factor",
            "1B Factor",
            "2B Factor",
            "3B Factor",
            "H Factor",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate ParkFactors.csv from seamheads park data."
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="First season to include (default: last 3 seasons).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Last season to include (default: latest season).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/parks/ParkFactors.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    home_path = Path("data/parks/Home_Main_Data_With_Parks Break.csv")
    visitor_path = Path("data/parks/Visitor_Main_Data.csv")
    park_config_path = Path("data/parks/ParkConfig.csv")

    if not home_path.exists() or not visitor_path.exists():
        raise SystemExit("Missing Home or Visitor data CSVs.")
    min_year, max_year = _year_bounds(home_path)
    if max_year == 0:
        raise SystemExit("No season data found in home data CSV.")

    end_year = args.end_year if args.end_year is not None else max_year
    start_year = args.start_year
    if start_year is None:
        start_year = max(end_year - 2, min_year)

    visitor_stats = _load_visitor_stats(visitor_path)
    park_names = _load_latest_park_names(park_config_path)
    aggs = compute_factors(home_path, visitor_stats, start_year, end_year)
    _write_factors(args.output, park_names, aggs, start_year, end_year)
    print(
        f"Wrote {args.output} for seasons {start_year}-{end_year} "
        f"({len(aggs)} parks)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
