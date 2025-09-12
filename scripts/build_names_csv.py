"""Generate data/names.csv from legacy name lists.

The script reads ``playbalance/FirstNames.txt`` and ``playbalance/Surnames.txt``
(containing census-style frequency tables) and emits ``data/names.csv``
with columns ``ethnicity,first_name,last_name``.  Names are normalized to
Title Case and paired with an ethnicity label (``Anglo``, ``African``,
``Asian`` or ``Hispanic``).

An internal mapping assigns a subset of names to non-Anglo ethnicities.
Any name not explicitly mapped defaults to ``Anglo``.  The resulting
CSV contains a sampled set of combinations from each group.  A different
limit may be provided as the first command-line argument.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path
from typing import Dict, Iterable, List

# Base paths
ROOT = Path(__file__).resolve().parents[1]
FIRST_NAMES = ROOT / "playbalance" / "FirstNames.txt"
SURNAMES = ROOT / "playbalance" / "Surnames.txt"
OUT_FILE = ROOT / "data" / "names.csv"

# Internal ethnicity mappings.  These sets intentionally contain only a
# small sample of names for demonstration.  Unmatched names default to
# ``Anglo``.
AFRICAN_FIRST = {
    "Darnell",
    "Deshawn",
    "Jamal",
    "Jermaine",
    "Leroy",
    "Malik",
    "Rasheed",
    "Tyrone",
    "Xavier",
    "Kwame",
    "Jalen",
    "Cedric",
    "Percy",
    "Rufus",
}

ASIAN_FIRST = {
    "Wei",
    "Hiro",
    "Kenji",
    "Min",
    "Sung",
    "Yuan",
    "Hiroshi",
    "Takashi",
    "Yoshi",
    "Jin",
    "Yong",
    "Aki",
    "Ling",
    "Chen",
    "Li",
}

HISPANIC_FIRST = {
    "Jose",
    "Juan",
    "Luis",
    "Carlos",
    "Miguel",
    "Jorge",
    "Pedro",
    "Manuel",
    "Francisco",
    "Antonio",
    "Roberto",
    "Ricardo",
    "Alejandro",
    "Fernando",
    "Raul",
    "Hector",
    "Rafael",
    "Eduardo",
}

AFRICAN_SUR = {
    "Washington",
    "Jefferson",
    "Jackson",
    "Harris",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Green",
    "Baker",
    "Carter",
    "Mitchell",
    "Taylor",
    "White",
    "Gaines",
}

ASIAN_SUR = {
    "Chen",
    "Li",
    "Wang",
    "Zhang",
    "Liu",
    "Kim",
    "Nguyen",
    "Tran",
    "Le",
    "Pham",
    "Tanaka",
    "Yamamoto",
    "Park",
    "Choi",
    "Singh",
    "Patel",
    "Khan",
    "Hassan",
    "Lin",
    "Huang",
}

HISPANIC_SUR = {
    "Garcia",
    "Martinez",
    "Rodriguez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Perez",
    "Sanchez",
    "Ramirez",
    "Torres",
    "Flores",
    "Rivera",
    "Gomez",
    "Diaz",
    "Reyes",
    "Cruz",
    "Ortiz",
    "Morales",
    "Vargas",
    "Castillo",
    "Vasquez",
    "Guerrero",
    "Mendoza",
    "Delgado",
    "Ramos",
}

ETHNICITIES = ["Anglo", "African", "Asian", "Hispanic"]

# Ensure the dataset always contains these specific Anglo name pairs which are
# referenced in tests and examples.
MANDATORY_PAIRS = [
    ("Anglo", "Frederick", "Sullivan"),
    ("Anglo", "Jim", "Thompson"),
]


def _parse_name_file(path: Path) -> List[str]:
    """Return a list of names from *path*."""

    names: List[str] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            token = line.split()[0]
            names.append(token.title())
    return names


def _classify_first(name: str) -> str:
    if name in AFRICAN_FIRST:
        return "African"
    if name in ASIAN_FIRST:
        return "Asian"
    if name in HISPANIC_FIRST:
        return "Hispanic"
    return "Anglo"


def _classify_surname(name: str) -> str:
    if name in AFRICAN_SUR:
        return "African"
    if name in ASIAN_SUR:
        return "Asian"
    if name in HISPANIC_SUR:
        return "Hispanic"
    return "Anglo"


def _group_names(names: Iterable[str], classifier) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {e: [] for e in ETHNICITIES}
    for n in names:
        grouped[classifier(n)].append(n)
    return grouped


def build_names(limit_per_eth: int = 2500) -> None:
    """Create ``data/names.csv`` using *limit_per_eth* pairs per ethnicity."""

    firsts = _group_names(_parse_name_file(FIRST_NAMES), _classify_first)
    lasts = _group_names(_parse_name_file(SURNAMES), _classify_surname)

    rows = []
    random.seed(0)
    for eth in ETHNICITIES:
        f_list = firsts.get(eth, [])
        l_list = lasts.get(eth, [])
        if not f_list or not l_list:
            continue
        target = min(limit_per_eth, len(f_list) * len(l_list))
        combos = set()
        while len(combos) < target:
            combos.add((random.choice(f_list), random.choice(l_list)))
        for first, last in sorted(combos):
            rows.append({
                "ethnicity": eth,
                "first_name": first,
                "last_name": last,
            })

    existing = {(r["ethnicity"], r["first_name"], r["last_name"]) for r in rows}
    for eth, first, last in MANDATORY_PAIRS:
        if (eth, first, last) not in existing:
            rows.append({"ethnicity": eth, "first_name": first, "last_name": last})

    rows.sort(key=lambda r: (r["ethnicity"], r["first_name"], r["last_name"]))

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ethnicity", "first_name", "last_name"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
    build_names(limit)
