"""
Generate basic ballpark diagrams from data/parks/ParkConfig.csv.

Usage examples:

- All latest-year parks:
  python -m scripts.generate_park_diagrams

- Specific year for all parks:
  python -m scripts.generate_park_diagrams --year 2024

- Specific park:
  python -m scripts.generate_park_diagrams --park-id ANA01 --year 2024

- Custom CSV or output directory:
  python -m scripts.generate_park_diagrams --csv data/parks/ParkConfig.csv --outdir images/parks

The diagrams are intentionally simple: foul lines, an outfield wall
polyline interpolated from available dimensions, and a minimal infield
diamond for context. This provides an at-a-glance reference that we can
use as a foundation for a future, editable stadium configuration UI.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


# Columns we map into angles across the outfield
# Angle convention: 0° = RF line (+x), 90° = LF line (+y), 45° = straightaway CF
ANGLE_MAP: List[Tuple[str, float]] = [
    ("RF_Dim", 0.0),
    ("SRF_Dim", 10.0),
    ("RFA_Dim", 20.0),
    ("RC_Dim", 30.0),
    ("RCC_Dim", 40.0),
    ("CF_Dim", 45.0),
    ("LCC_Dim", 50.0),
    ("LC_Dim", 60.0),
    ("LFA_Dim", 70.0),
    ("SLF_Dim", 80.0),
    ("LF_Dim", 90.0),
]


@dataclass
class ParkRow:
    park_id: str
    name: str
    year: int
    dims: Dict[str, float]


def _parse_float(value: str) -> Optional[float]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_parks(csv_path: Path) -> List[ParkRow]:
    parks: List[ParkRow] = []
    with csv_path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                year = int(row.get("Year") or 0)
            except (TypeError, ValueError):
                continue

            dims: Dict[str, float] = {}
            for key, _ in ANGLE_MAP:
                val = _parse_float(row.get(key, ""))
                if val is not None:
                    dims[key] = val

            parks.append(
                ParkRow(
                    park_id=(row.get("parkID") or row.get("ParkID") or "").strip(),
                    name=(row.get("NAME") or row.get("Name") or "").strip(),
                    year=year,
                    dims=dims,
                )
            )
    return parks


def latest_by_park(parks: Iterable[ParkRow]) -> List[ParkRow]:
    best: Dict[str, ParkRow] = {}
    for p in parks:
        if not p.park_id:
            continue
        if p.park_id not in best or p.year > best[p.park_id].year:
            best[p.park_id] = p
    return list(best.values())


def points_for_row(row: ParkRow) -> List[Tuple[float, float]]:
    pts: List[Tuple[float, float]] = []
    for key, deg in ANGLE_MAP:
        r = row.dims.get(key)
        if r is None:
            continue
        rad = math.radians(deg)
        x = r * math.cos(rad)
        y = r * math.sin(rad)
        pts.append((x, y))
    # Ensure points progress from RF->LF along increasing angle
    return pts


def _compute_scale(
    points: List[Tuple[float, float]], width: int, height: int, margin: int
) -> float:
    if not points:
        return 1.0
    max_x = max(p[0] for p in points)
    max_y = max(p[1] for p in points)
    # Fit within drawable area
    sx = (width - 2 * margin) / max(1.0, max_x)
    sy = (height - 2 * margin) / max(1.0, max_y)
    return min(sx, sy)


def _to_img_coords(
    pt: Tuple[float, float], scale: float, height: int, margin: int
) -> Tuple[int, int]:
    x, y = pt
    ix = int(round(margin + x * scale))
    iy = int(round(height - margin - y * scale))  # invert Y for image coords
    return ix, iy


def draw_diagram(
    row: ParkRow,
    out_path: Path,
    size: Tuple[int, int] = (800, 800),
    margin: int = 50,
) -> None:
    width, height = size
    img = Image.new("RGB", size, (242, 242, 242))
    draw = ImageDraw.Draw(img)

    pts_field = points_for_row(row)
    if not pts_field:
        # Nothing to draw; create a label-only card
        _label_only(img, draw, row)
        img.save(out_path)
        return

    scale = _compute_scale(pts_field, width, height, margin)

    # Draw infield diamond for context (90ft square rotated 45°)
    base = 90.0
    diamond = [
        (0.0, 0.0),  # Home
        (base, 0.0),  # First
        (base, base),  # Second
        (0.0, base),  # Third
    ]
    diamond_img = [_to_img_coords(p, scale, height, margin) for p in diamond]
    draw.polygon(diamond_img, outline=(160, 120, 60), fill=(205, 173, 125))

    # Foul lines to RF and LF corners
    rf = next(((x, 0.0) for x in [row.dims.get("RF_Dim") or 0.0] if x), (0.0, 0.0))
    lf = next(((0.0, y) for y in [row.dims.get("LF_Dim") or 0.0] if y), (0.0, 0.0))
    home_img = _to_img_coords((0.0, 0.0), scale, height, margin)
    rf_img = _to_img_coords(rf, scale, height, margin)
    lf_img = _to_img_coords(lf, scale, height, margin)
    draw.line([home_img, rf_img], fill=(80, 80, 80), width=2)
    draw.line([home_img, lf_img], fill=(80, 80, 80), width=2)

    # Outfield wall polyline from RF -> ... -> LF
    wall = [_to_img_coords(p, scale, height, margin) for p in pts_field]
    draw.line(wall, fill=(20, 110, 20), width=4, joint="curve")

    # Center field guide
    if "CF_Dim" in row.dims:
        cf = _to_img_coords(
            (
                row.dims["CF_Dim"] / math.sqrt(2),
                row.dims["CF_Dim"] / math.sqrt(2),
            ),
            scale,
            height,
            margin,
        )
        draw.ellipse([cf[0] - 3, cf[1] - 3, cf[0] + 3, cf[1] + 3], fill=(0, 90, 180))

    # Title and metadata
    _draw_label(img, draw, row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def _label_only(img: Image.Image, draw: ImageDraw.ImageDraw, row: ParkRow) -> None:
    _draw_label(img, draw, row)


def _draw_label(img: Image.Image, draw: ImageDraw.ImageDraw, row: ParkRow) -> None:
    title = f"{row.name or row.park_id} ({row.year})"
    subtitle = _subtitle_from_dims(row.dims)
    try:
        font_title = ImageFont.truetype("arial.ttf", 18)
        font_sub = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Shadow for readability
    draw.text((16, 16), title, fill=(0, 0, 0), font=font_title)
    draw.text((15, 15), title, fill=(15, 15, 15), font=font_title)
    draw.text((16, 44), subtitle, fill=(0, 0, 0), font=font_sub)
    draw.text((15, 43), subtitle, fill=(30, 30, 30), font=font_sub)


def _subtitle_from_dims(dims: Dict[str, float]) -> str:
    def get(k: str) -> Optional[int]:
        v = dims.get(k)
        return int(round(v)) if v is not None else None

    left = get("LF_Dim")
    center = get("CF_Dim")
    right = get("RF_Dim")
    parts = []
    if left is not None:
        parts.append(f"LF {left}ft")
    if center is not None:
        parts.append(f"CF {center}ft")
    if right is not None:
        parts.append(f"RF {right}ft")
    return " | ".join(parts)


def _resolve_paths(csv_arg: Optional[str], outdir_arg: Optional[str]) -> Tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    csv_path = Path(csv_arg) if csv_arg else root / "data" / "parks" / "ParkConfig.csv"
    outdir = Path(outdir_arg) if outdir_arg else root / "images" / "parks"
    return csv_path, outdir


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate ballpark diagrams from CSV")
    parser.add_argument("--csv", help="Path to ParkConfig.csv", default=None)
    parser.add_argument("--outdir", help="Output directory for images", default=None)
    parser.add_argument("--year", type=int, help="Filter to year (e.g., 2024)")
    parser.add_argument("--park-id", help="Filter to a single park ID")
    args = parser.parse_args(argv)

    csv_path, outdir = _resolve_paths(args.csv, args.outdir)
    parks = load_parks(csv_path)

    if args.year:
        parks = [p for p in parks if p.year == args.year]
    else:
        # Use latest year per park by default
        parks = latest_by_park(parks)

    if args.park_id:
        parks = [p for p in parks if p.park_id == args.park_id]

    if not parks:
        print("No park rows matched filters.")
        return 1

    for p in parks:
        fname = f"{p.park_id}_{p.year}.png" if p.park_id else f"park_{p.year}.png"
        out_path = outdir / fname
        draw_diagram(p, out_path)
        print(f"Wrote {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

