from __future__ import annotations

from bisect import bisect_left
import csv
from functools import lru_cache
import os
from pathlib import Path
from typing import Dict, List, Optional

from models.pitcher import Pitcher
from models.player import Player
from utils.path_utils import get_base_dir

DISPLAY_ENV = "PB_RATING_DISPLAY"

_ABBREV_MAP = {
    "as": "arm",
    "en": "endurance",
    "co": "control",
    "mo": "movement",
    "mv": "movement",
}

_PITCH_KEYS = {"fb", "sl", "cu", "cb", "si", "scb", "kn"}
_HITTER_KEYS = {key for key in Player._rating_fields if not key.startswith("pot_")}
_PITCHER_KEYS = {key for key in Pitcher._rating_fields if not key.startswith("pot_")}
_ALL_KEYS = _HITTER_KEYS | _PITCHER_KEYS


def _rating_source_path() -> Path:
    base_dir = get_base_dir()
    normalized = base_dir / "data" / "players_normalized.csv"
    if normalized.exists():
        return normalized
    return base_dir / "data" / "players.csv"


@lru_cache(maxsize=1)
def _load_distributions() -> Dict[str, Dict[str, List[int]]]:
    distributions = {
        "hitters": {key: [] for key in _HITTER_KEYS},
        "pitchers": {key: [] for key in _PITCHER_KEYS},
        "all": {key: [] for key in _ALL_KEYS},
    }
    path = _rating_source_path()
    if not path.exists():
        return distributions

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            is_pitcher = str(row.get("is_pitcher", "0")).strip().lower() in {
                "1",
                "true",
                "yes",
            }
            keys = _PITCHER_KEYS if is_pitcher else _HITTER_KEYS
            for key in keys:
                raw = row.get(key)
                if raw in (None, ""):
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    continue
                if key in _PITCH_KEYS and value <= 0:
                    continue
                rating = int(round(value))
                distributions["all"][key].append(rating)
                if is_pitcher:
                    distributions["pitchers"][key].append(rating)
                else:
                    distributions["hitters"][key].append(rating)

    for group in distributions.values():
        for values in group.values():
            values.sort()
    return distributions


def _normalize_key(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    token = key.strip().lower()
    token = token.replace("/", " ").replace("-", " ").replace(":", " ")
    token = " ".join(token.split())
    token = token.replace(" ", "_")
    if token.startswith("pot_"):
        token = token[4:]
    return _ABBREV_MAP.get(token, token)


def _percentile(values: List[int], value: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return 1.0
    idx = bisect_left(values, value)
    if idx <= 0:
        return 0.0
    if idx >= len(values) - 1:
        return 1.0
    return idx / (len(values) - 1)


def _select_distribution(key: str, is_pitcher: Optional[bool]) -> List[int]:
    distributions = _load_distributions()
    if is_pitcher is True:
        values = distributions["pitchers"].get(key, [])
    elif is_pitcher is False:
        values = distributions["hitters"].get(key, [])
    else:
        values = distributions["all"].get(key, [])
    if values:
        return values
    if is_pitcher is not None:
        return distributions["all"].get(key, [])
    return (
        distributions["pitchers"].get(key, [])
        or distributions["hitters"].get(key, [])
        or []
    )


def _normalize_mode(raw: str) -> str:
    token = (raw or "").strip().lower()
    if not token:
        return "scale_99"
    if token in {"raw", "backend", "normalized"}:
        return "raw"
    if token in {
        "99",
        "0-99",
        "scale_99",
        "display_99",
        "percentile",
        "percentile_99",
    }:
        return "scale_99"
    if token in {"stars", "star", "asterisks", "asterisk"}:
        return "stars"
    return "scale_99"


def get_display_mode(override: Optional[str] = None) -> str:
    if override is not None:
        return _normalize_mode(override)
    return _normalize_mode(os.getenv(DISPLAY_ENV, "scale_99"))


def rating_display_value(
    value: object,
    *,
    key: Optional[str] = None,
    is_pitcher: Optional[bool] = None,
    mode: Optional[str] = None,
) -> object:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "" if value is None else str(value)

    display_mode = get_display_mode(mode)
    normalized_key = _normalize_key(key)
    if display_mode == "raw" or not normalized_key:
        return int(round(numeric))

    if normalized_key in _PITCH_KEYS and numeric <= 0:
        return 0

    values = _select_distribution(normalized_key, is_pitcher)
    pct = _percentile(values, numeric)
    if pct is None:
        return int(round(numeric))

    if display_mode == "stars":
        stars = min(5, max(1, int(pct * 5) + 1))
        return "*" * stars

    scaled = int(round(pct * 99))
    return max(0, min(99, scaled))


def rating_display_text(
    value: object,
    *,
    key: Optional[str] = None,
    is_pitcher: Optional[bool] = None,
    mode: Optional[str] = None,
) -> str:
    return str(rating_display_value(value, key=key, is_pitcher=is_pitcher, mode=mode))
