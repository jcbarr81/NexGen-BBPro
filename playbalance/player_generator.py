# ARR-inspired Player Generator Script
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set, Optional
import csv
from pathlib import Path

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - optional dependency for CLI usage
    pd = None

from utils.path_utils import get_base_dir

# Constants
BASE_DIR = get_base_dir()
NAME_PATH = BASE_DIR / "data" / "names.csv"
PLAYER_PATH = BASE_DIR / "data" / "players.csv"
POSITION_AVERAGE_PATH = (
    BASE_DIR
    / "data"
    / "MLB_avg"
    / "mlb_position_averages_2021-2025YTD.csv"
)


def _load_position_averages(path: Path) -> Dict[str, Dict[str, float]]:
    """Return MLB average hitting stats by position to guide rating guardrails."""

    data: Dict[str, Dict[str, float]] = {}
    if not path.exists():
        return data
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            position = (row.get("Position") or "").strip()
            if not position:
                continue
            stats: Dict[str, float] = {}
            for key in ("AVG", "OBP", "SLG", "OPS", "wRC+"):
                raw = row.get(key)
                if raw in (None, ""):
                    continue
                try:
                    stats[key] = float(raw)
                except ValueError:
                    continue
            if stats:
                data[position] = stats
    return data


POSITION_AVERAGES = _load_position_averages(POSITION_AVERAGE_PATH)

if not POSITION_AVERAGES:
    POSITION_AVERAGES = {
        "C": {"AVG": 0.233, "OBP": 0.302, "SLG": 0.383, "OPS": 0.685, "wRC+": 90.0},
        "1B": {"AVG": 0.251, "OBP": 0.328, "SLG": 0.427, "OPS": 0.755, "wRC+": 109.0},
        "2B": {"AVG": 0.247, "OBP": 0.313, "SLG": 0.384, "OPS": 0.698, "wRC+": 94.0},
        "3B": {"AVG": 0.245, "OBP": 0.314, "SLG": 0.404, "OPS": 0.719, "wRC+": 99.0},
        "SS": {"AVG": 0.253, "OBP": 0.315, "SLG": 0.401, "OPS": 0.716, "wRC+": 98.0},
        "LF": {"AVG": 0.244, "OBP": 0.319, "SLG": 0.404, "OPS": 0.723, "wRC+": 101.0},
        "CF": {"AVG": 0.242, "OBP": 0.309, "SLG": 0.398, "OPS": 0.708, "wRC+": 96.0},
        "RF": {"AVG": 0.247, "OBP": 0.320, "SLG": 0.425, "OPS": 0.745, "wRC+": 106.0},
        "DH": {"AVG": 0.249, "OBP": 0.330, "SLG": 0.442, "OPS": 0.772, "wRC+": 114.0},
        "P": {"AVG": 0.108, "OBP": 0.147, "SLG": 0.137, "OPS": 0.284},
    }


def _stat_bounds(field: str, include_pitchers: bool = False) -> Tuple[float, float]:
    values = [
        stats[field]
        for pos, stats in POSITION_AVERAGES.items()
        if field in stats and (include_pitchers or pos != "P")
    ]
    if not values:
        return 0.0, 1.0
    return min(values), max(values)


def _scale_stat(
    value: float,
    min_src: float,
    max_src: float,
    min_dest: float,
    max_dest: float,
) -> float:
    if max_src <= min_src:
        return (min_dest + max_dest) / 2.0
    normalized = (value - min_src) / (max_src - min_src)
    normalized = max(0.0, min(1.0, normalized))
    return min_dest + normalized * (max_dest - min_dest)


def _sample_rating(
    center: float,
    *,
    floor: int,
    ceiling: int,
    spread: float = 6.0,
    outlier_chance: float = 0.04,
    outlier_bounds: Tuple[int, int] = (72, 90),
) -> Tuple[int, bool]:
    rating = int(round(random.gauss(center, spread)))
    rating = max(floor, min(ceiling, rating))
    outlier = False
    if random.random() < outlier_chance:
        outlier = True
        rating = random.randint(outlier_bounds[0], outlier_bounds[1])
    rating = max(20, min(95, rating))
    return rating, outlier


def _build_hitter_guardrails() -> Dict[str, Dict[str, float]]:
    guardrails: Dict[str, Dict[str, float]] = {}
    avg_min, avg_max = _stat_bounds("AVG")
    slg_min, slg_max = _stat_bounds("SLG")
    ops_min, ops_max = _stat_bounds("OPS")
    for pos, stats in POSITION_AVERAGES.items():
        if pos == "P":
            continue
        contact_center = _scale_stat(stats["AVG"], avg_min, avg_max, 52, 70)
        power_center = _scale_stat(stats["SLG"], slg_min, slg_max, 50, 72)
        speed_center = _scale_stat(stats["OPS"], ops_min, ops_max, 48, 68)
        if pos in {"CF", "SS"}:
            speed_center += 4
        elif pos in {"2B", "LF"}:
            speed_center += 2
        elif pos in {"C", "1B", "DH"}:
            speed_center -= 5
        guardrails[pos] = {
            "contact_center": contact_center,
            "power_center": power_center,
            "speed_center": max(45, min(70, speed_center)),
        }
    return guardrails


HITTER_GUARDRAILS = _build_hitter_guardrails()
DEFAULT_HITTER_GUARDRAIL = {"contact_center": 52.0, "power_center": 52.0, "speed_center": 50.0}


def _load_name_pool() -> Dict[str, List[Tuple[str, str]]]:
    pool: Dict[str, List[Tuple[str, str]]] = {}
    source = PLAYER_PATH if PLAYER_PATH.exists() else NAME_PATH
    if source.exists():
        with source.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ethnicity = row.get("ethnicity", "").strip()
                first = row.get("first_name")
                last = row.get("last_name")
                if ethnicity and first and last:
                    pool.setdefault(ethnicity, []).append((first, last))
    return pool


name_pool = _load_name_pool()
used_names: Set[Tuple[str, str]] = set()

# Age generation tables derived from the original ARR configuration.  Each
# entry maps a player type to a ``(base, num_dice, num_sides)`` tuple used when
# rolling the player's age.  The final age is ``base`` plus the total of the
# dice rolls.
AGE_TABLES: Dict[str, Tuple[int, int, int]] = {
    "amateur": (14, 3, 3),
    "fictional": (14, 4, 6),
    "filler": (17, 4, 6),
}


def reset_name_cache():
    global name_pool, used_names
    name_pool = _load_name_pool()
    used_names = set()

    
# Helper Functions

def generate_birthdate(
    age_range: Optional[Tuple[int, int]] = None,
    player_type: str = "fictional",
):
    """Generate a birthdate and age.

    Parameters
    ----------
    age_range:
        Optional explicit ``(min_age, max_age)`` bounds.  If provided the age
        is chosen uniformly from within the range.
    player_type:
        When ``age_range`` is not supplied the player's age is determined by
        rolling dice according to the table for the given ``player_type``.
    """

    today = datetime.today()
    if age_range is not None:
        age = random.randint(*age_range)
    else:
        base, num_dice, num_sides = AGE_TABLES[player_type]
        age = base + sum(random.randint(1, num_sides) for _ in range(num_dice))

    days_old = age * 365 + random.randint(0, 364)
    birthdate = (today - timedelta(days=days_old)).date()
    return birthdate, age

def bounded_rating(min_val=10, max_val=99):
    return random.randint(min_val, max_val)

def bounded_potential(actual, age):
    if age < 22:
        pot = actual + random.randint(10, 30)
    elif age < 28:
        pot = actual + random.randint(5, 15)
    elif age < 32:
        pot = actual + random.randint(-5, 5)
    else:
        pot = actual - random.randint(0, 10)
    return max(10, min(99, pot))


def roll_dice(base: int, count: int, faces: int) -> int:
    """Return ``base`` plus the total from rolling ``count`` ``faces``-sided dice."""

    return base + sum(random.randint(1, faces) for _ in range(count))

def generate_name() -> tuple[str, str, str]:
    """Return a unique ``(first, last, ethnicity)`` tuple."""

    if name_pool:
        total_names = sum(len(v) for v in name_pool.values())
        if len(used_names) >= total_names:
            return "John", "Doe", "Unknown"
        while True:
            ethnicity = random.choice(list(name_pool.keys()))
            first, last = random.choice(name_pool[ethnicity])
            if (first, last) not in used_names:
                used_names.add((first, last))
                return first, last, ethnicity
    return "John", "Doe", "Unknown"


def _adjust_endurance(endurance: int) -> int:
    """Apply ARR-based endurance adjustments (lines 176-180).

    Pitchers with endurance between 30 and 69 have a 50% chance to have their
    rating adjusted by adding or subtracting 1–20 points.  The result is always
    clamped to the 1–99 range.
    """

    if 30 <= endurance <= 69 and random.randint(1, 100) <= 50:
        delta = random.randint(1, 20)
        if random.choice([-1, 1]) < 0:
            endurance -= delta
        else:
            endurance += delta
    return max(1, min(99, endurance))

PRIMARY_POSITION_WEIGHTS = {
    "C": 19,
    "1B": 15,
    "2B": 14,
    "SS": 13,
    "3B": 14,
    "LF": 16,
    "CF": 13,
    "RF": 16,
}

# Weights used for distributing rating points among player attributes.  These
# values were taken from the original ARR data file (lines 71-86) and represent
# how many parts of a shared rating pool should be assigned to each attribute.
HITTER_RATING_WEIGHTS: Dict[str, Dict[str, int]] = {
    "P": {"ch": 40, "ph": 107, "sp": 393, "fa": 557, "arm": 0},
    "C": {"ch": 189, "ph": 163, "sp": 166, "fa": 214, "arm": 269},
    "1B": {"ch": 213, "ph": 178, "sp": 163, "fa": 226, "arm": 221},
    "2B": {"ch": 200, "ph": 135, "sp": 206, "fa": 220, "arm": 239},
    "SS": {"ch": 187, "ph": 133, "sp": 199, "fa": 225, "arm": 256},
    "3B": {"ch": 201, "ph": 162, "sp": 175, "fa": 221, "arm": 240},
    "LF": {"ch": 195, "ph": 165, "sp": 202, "fa": 218, "arm": 220},
    "CF": {"ch": 202, "ph": 144, "sp": 235, "fa": 206, "arm": 213},
    "RF": {"ch": 193, "ph": 175, "sp": 187, "fa": 212, "arm": 233},
}

PITCHER_RATING_WEIGHTS: Dict[str, int] = {
    "endurance": 196,
    "control": 206,
    "hold_runner": 184,
    "movement": 184,
    "arm": 228,
}


def distribute_rating_points(total: int, weights: Dict[str, int]) -> Dict[str, int]:
    """Distribute ``total`` rating points according to ``weights``.

    Parameters
    ----------
    total: int
        Total number of rating points to distribute.
    weights: Dict[str, int]
        Mapping of attribute name to weight.  The resulting dictionary will
        contain the same keys with integer values summing to ``total``.
    """

    total_weight = sum(weights.values())
    remaining = total
    items = list(weights.items())
    allocations: Dict[str, int] = {}

    for attr, weight in items[:-1]:
        value = round(total * weight / total_weight)
        allocations[attr] = value
        remaining -= value

    # The final attribute takes whatever points remain so the totals match.
    last_attr = items[-1][0]
    allocations[last_attr] = remaining
    return allocations

PITCHER_RATE = 0.4  # Fraction of draft pool that should be pitchers

# Appearance tables keyed by ethnicity. The ``"Default"`` entry is used when an
# ethnicity is not explicitly listed.
SKIN_TONE_WEIGHTS: Dict[str, Dict[str, int]] = {
    "Anglo": {"light": 60, "medium": 30, "dark": 10},
    "African": {"light": 5, "medium": 15, "dark": 80},
    "Asian": {"light": 40, "medium": 55, "dark": 5},
    "Hispanic": {"light": 30, "medium": 50, "dark": 20},
    "Default": {"light": 33, "medium": 34, "dark": 33},
}

HAIR_COLOR_WEIGHTS: Dict[str, Dict[str, int]] = {
    "Anglo": {"blonde": 25, "brown": 40, "black": 25, "red": 10},
    "African": {"black": 80, "brown": 20},
    "Asian": {"black": 90, "brown": 10},
    "Hispanic": {"black": 40, "brown": 40, "blonde": 15, "red": 5},
    "Default": {"black": 40, "brown": 40, "blonde": 15, "red": 5},
}

FACIAL_HAIR_WEIGHTS: Dict[str, Dict[str, int]] = {
    "Anglo": {"clean_shaven": 60, "mustache": 10, "goatee": 10, "beard": 20},
    "African": {"clean_shaven": 55, "mustache": 15, "goatee": 10, "beard": 20},
    "Asian": {"clean_shaven": 70, "mustache": 10, "goatee": 10, "beard": 10},
    "Hispanic": {"clean_shaven": 55, "mustache": 15, "goatee": 15, "beard": 15},
    "Default": {"clean_shaven": 60, "mustache": 10, "goatee": 10, "beard": 20},
}


def assign_primary_position() -> str:
    """Select a primary position using weights from the ARR tables."""
    return random.choices(
        list(PRIMARY_POSITION_WEIGHTS.keys()),
        weights=PRIMARY_POSITION_WEIGHTS.values(),
    )[0]


def _lookup_weights(table: Dict[str, Dict[str, int]], ethnicity: str) -> Dict[str, int]:
    """Return the weight mapping for ``ethnicity`` falling back to ``Default``."""

    return table.get(ethnicity, table["Default"])


def assign_skin_tone(ethnicity: str) -> str:
    """Select a skin tone using ethnicity-specific weights."""

    weights = _lookup_weights(SKIN_TONE_WEIGHTS, ethnicity)
    return random.choices(list(weights.keys()), weights=weights.values())[0]


def assign_hair_color(ethnicity: str) -> str:
    """Select a hair color using ethnicity-specific weights."""

    weights = _lookup_weights(HAIR_COLOR_WEIGHTS, ethnicity)
    return random.choices(list(weights.keys()), weights=weights.values())[0]


def assign_facial_hair(ethnicity: str, age: int) -> str:
    """Select facial hair style using ethnicity-specific weights.

    Younger players tend to be clean shaven while older players are more likely
    to sport mustaches or beards.
    """

    weights = _lookup_weights(FACIAL_HAIR_WEIGHTS, ethnicity).copy()
    if age < 25:
        weights["clean_shaven"] += 20
        weights["beard"] = max(0, weights.get("beard", 0) - 10)
    elif age > 35:
        weights["mustache"] += 10
        weights["beard"] += 10
        weights["clean_shaven"] = max(0, weights.get("clean_shaven", 0) - 20)
    return random.choices(list(weights.keys()), weights=weights.values())[0]


BATS_THROWS: Dict[str, List[Tuple[str, str, int]]] = {
    "P": [
        ("R", "L", 1),
        ("R", "R", 50),
        ("L", "L", 25),
        ("L", "R", 10),
        ("S", "L", 4),
        ("S", "R", 10),
    ],
    "C": [
        ("R", "L", 0),
        ("R", "R", 75),
        ("L", "L", 0),
        ("L", "R", 15),
        ("S", "L", 0),
        ("S", "R", 10),
    ],
    "1B": [
        ("R", "L", 1),
        ("R", "R", 40),
        ("L", "L", 32),
        ("L", "R", 13),
        ("S", "L", 4),
        ("S", "R", 10),
    ],
    "2B": [
        ("R", "L", 0),
        ("R", "R", 75),
        ("L", "L", 0),
        ("L", "R", 15),
        ("S", "L", 0),
        ("S", "R", 10),
    ],
    "3B": [
        ("R", "L", 0),
        ("R", "R", 75),
        ("L", "L", 0),
        ("L", "R", 15),
        ("S", "L", 0),
        ("S", "R", 10),
    ],
    "SS": [
        ("R", "L", 0),
        ("R", "R", 75),
        ("L", "L", 0),
        ("L", "R", 15),
        ("S", "L", 0),
        ("S", "R", 10),
    ],
    "LF": [
        ("R", "L", 1),
        ("R", "R", 50),
        ("L", "L", 25),
        ("L", "R", 10),
        ("S", "L", 4),
        ("S", "R", 10),
    ],
    "CF": [
        ("R", "L", 1),
        ("R", "R", 50),
        ("L", "L", 25),
        ("L", "R", 10),
        ("S", "L", 4),
        ("S", "R", 10),
    ],
    "RF": [
        ("R", "L", 1),
        ("R", "R", 50),
        ("L", "L", 25),
        ("L", "R", 10),
        ("S", "L", 4),
        ("S", "R", 10),
    ],
}


FIELDING_POTENTIAL_MATRIX: Dict[str, Dict[str, int]] = {
    "P": {"P": 0, "C": 10, "1B": 100, "2B": 20, "3B": 60, "SS": 10, "LF": 90, "CF": 40, "RF": 80},
    "C": {"P": 60, "C": 0, "1B": 100, "2B": 20, "3B": 60, "SS": 10, "LF": 90, "CF": 40, "RF": 80},
    "1B": {"P": 60, "C": 10, "1B": 0, "2B": 20, "3B": 60, "SS": 10, "LF": 90, "CF": 40, "RF": 80},
    "2B": {"P": 130, "C": 10, "1B": 160, "2B": 0, "3B": 130, "SS": 90, "LF": 150, "CF": 120, "RF": 140},
    "3B": {"P": 100, "C": 10, "1B": 140, "2B": 90, "3B": 0, "SS": 80, "LF": 130, "CF": 100, "RF": 120},
    "SS": {"P": 140, "C": 10, "1B": 170, "2B": 100, "3B": 140, "SS": 0, "LF": 160, "CF": 120, "RF": 150},
    "LF": {"P": 90, "C": 10, "1B": 120, "2B": 60, "3B": 90, "SS": 40, "LF": 0, "CF": 80, "RF": 100},
    "CF": {"P": 110, "C": 10, "1B": 150, "2B": 80, "3B": 110, "SS": 70, "LF": 140, "CF": 0, "RF": 130},
    "RF": {"P": 90, "C": 10, "1B": 130, "2B": 60, "3B": 90, "SS": 40, "LF": 110, "CF": 80, "RF": 0},
}

ALL_POSITIONS = list(FIELDING_POTENTIAL_MATRIX["P"].keys())


def assign_bats_throws(primary: str) -> Tuple[str, str]:
    combos = BATS_THROWS.get(primary, BATS_THROWS["1B"])
    bats, throws, _ = random.choices(
        combos, weights=[c[2] for c in combos]
    )[0]
    return bats, throws


SECONDARY_POSITIONS: Dict[str, Dict[str, Dict[str, int]]] = {
    "P": {"chance": 1, "weights": {"1B": 30, "LF": 25, "RF": 45}},
    "C": {"chance": 2, "weights": {"1B": 30, "3B": 20, "LF": 20, "RF": 30}},
    "1B": {"chance": 2, "weights": {"C": 5, "3B": 15, "LF": 50, "RF": 30}},
    "2B": {"chance": 5, "weights": {"3B": 40, "SS": 50, "CF": 10}},
    "3B": {
        "chance": 5,
        "weights": {"C": 5, "1B": 15, "2B": 20, "SS": 10, "LF": 25, "RF": 25},
    },
    "SS": {"chance": 5, "weights": {"2B": 50, "3B": 40, "CF": 10}},
    "LF": {"chance": 9, "weights": {"C": 5, "1B": 25, "3B": 15, "CF": 20, "RF": 35}},
    "CF": {"chance": 6, "weights": {"2B": 10, "SS": 10, "LF": 40, "RF": 40}},
    "RF": {"chance": 9, "weights": {"C": 5, "1B": 25, "3B": 15, "LF": 35, "CF": 20}},
}


def assign_secondary_positions(primary: str) -> List[str]:
    info = SECONDARY_POSITIONS.get(primary)
    if not info:
        return []
    if random.randint(1, 100) > info["chance"]:
        return []
    positions = list(info["weights"].keys())
    weights = list(info["weights"].values())
    return [random.choices(positions, weights=weights)[0]]

PITCH_LIST = ["fb", "si", "cu", "cb", "sl", "kn", "sc"]


def _guardrail_for_position(position: str) -> Dict[str, float]:
    return HITTER_GUARDRAILS.get(position, HITTER_GUARDRAILS.get("CF", DEFAULT_HITTER_GUARDRAIL))


def _generate_hitter_ratings(primary_pos: str) -> Dict[str, int]:
    """Derive hitter ratings anchored to MLB positional averages with mild variance."""
    guardrail = _guardrail_for_position(primary_pos)
    contact, contact_outlier = _sample_rating(
        guardrail["contact_center"],
        floor=42,
        ceiling=78,
        spread=6.0,
        outlier_bounds=(75, 92),
    )
    power, _ = _sample_rating(
        guardrail["power_center"],
        floor=40,
        ceiling=78,
        spread=6.2,
        outlier_bounds=(74, 92),
    )
    speed, speed_outlier = _sample_rating(
        guardrail["speed_center"],
        floor=38,
        ceiling=72,
        spread=5.8,
        outlier_bounds=(74, 90),
    )
    if contact > 85 and speed > 85:
        if contact_outlier and speed_outlier:
            if guardrail["speed_center"] >= guardrail["contact_center"]:
                contact = max(
                    65,
                    min(
                        83,
                        int(round(random.gauss(guardrail["contact_center"], 4.0))),
                    ),
                )
            else:
                speed = max(
                    65,
                    min(
                        83,
                        int(round(random.gauss(guardrail["speed_center"], 4.0))),
                    ),
                )
        else:
            speed = max(
                65,
                min(83, int(round(random.gauss(guardrail["speed_center"], 4.0)))),
            )
    fielding_center = guardrail["speed_center"]
    if primary_pos in {"SS", "CF"}:
        fielding_center += 2
    elif primary_pos in {"2B", "LF"}:
        fielding_center += 1
    elif primary_pos in {"1B", "DH"}:
        fielding_center -= 5
    fielding, _ = _sample_rating(
        fielding_center,
        floor=32,
        ceiling=72,
        spread=5.2,
        outlier_bounds=(70, 86),
    )
    arm_center = guardrail["power_center"]
    if primary_pos in {"RF", "C"}:
        arm_center += 5
    elif primary_pos in {"3B", "LF"}:
        arm_center += 2
    elif primary_pos in {"1B"}:
        arm_center -= 5
    arm, _ = _sample_rating(
        arm_center,
        floor=38,
        ceiling=80,
        spread=5.5,
        outlier_bounds=(74, 92),
    )
    return {
        "ch": contact,
        "ph": power,
        "sp": speed,
        "fa": fielding,
        "arm": arm,
    }


def _generate_pitcher_core_ratings(throws: str) -> Dict[str, int]:
    """Return core pitcher ratings with floors centered near league-average performance."""
    endurance, _ = _sample_rating(
        60,
        floor=48,
        ceiling=80,
        spread=6.0,
        outlier_bounds=(78, 92),
    )
    endurance = _adjust_endurance(endurance)
    control, _ = _sample_rating(
        62,
        floor=50,
        ceiling=80,
        spread=5.2,
        outlier_bounds=(76, 92),
    )
    movement, _ = _sample_rating(
        64,
        floor=52,
        ceiling=82,
        spread=5.4,
        outlier_bounds=(78, 94),
    )
    if throws == "L":
        movement = min(92, movement + 4)
        control = max(50, control - 4)
    hold_runner, _ = _sample_rating(
        54,
        floor=42,
        ceiling=72,
        spread=5.0,
        outlier_bounds=(70, 86),
    )
    arm, _ = _sample_rating(
        64,
        floor=50,
        ceiling=85,
        spread=5.8,
        outlier_bounds=(80, 94),
    )
    fielding, _ = _sample_rating(
        54,
        floor=40,
        ceiling=74,
        spread=5.0,
        outlier_bounds=(72, 86),
    )
    return {
        "endurance": endurance,
        "control": control,
        "movement": movement,
        "hold_runner": hold_runner,
        "arm": arm,
        "fa": fielding,
    }


def generate_fielding_potentials(primary: str, others: List[str]) -> Dict[str, int]:
    matrix = FIELDING_POTENTIAL_MATRIX.get(primary, {})
    potentials: Dict[str, int] = {}
    for pos, value in matrix.items():
        if pos == primary or pos in others:
            continue
        potentials[pos] = value
    return potentials

PITCH_WEIGHTS = {
    ("L", "overhand"): {"fb": 512, "si": 112, "cu": 168, "cb": 164, "sl": 138, "kn": 1, "sc": 13},
    ("L", "sidearm"): {"fb": 512, "si": 168, "cu": 112, "cb": 138, "sl": 164, "kn": 1, "sc": 11},
    ("R", "overhand"): {"fb": 512, "si": 112, "cu": 168, "cb": 164, "sl": 138, "kn": 13, "sc": 1},
    ("R", "sidearm"): {"fb": 512, "si": 168, "cu": 112, "cb": 138, "sl": 164, "kn": 13, "sc": 1},
}


def _weighted_choice(weight_dict: Dict[str, int]) -> str:
    total = sum(weight_dict.values())
    r = random.uniform(0, total)
    upto = 0
    for item, weight in weight_dict.items():
        if upto + weight >= r:
            return item
        upto += weight
    return item  # pragma: no cover


def generate_pitches(throws: str, delivery: str, age: int):
    """Generate pitch ratings without exceeding rating caps.

    The previous implementation allocated points from a large pool which often
    resulted in fastball (``fb``) ratings above 99 that were immediately capped,
    producing identical ``fb`` and ``arm`` values for every pitcher.  This
    version assigns ratings to each selected pitch independently using bounded
    random values so that fastball and arm strength vary naturally.
    """

    weights = PITCH_WEIGHTS[(throws, delivery)]
    num_pitches = random.randint(2, 5)

    selected = ["fb"]
    available = list(weights.keys())
    available.remove("fb")
    for _ in range(num_pitches - 1):
        pitch = random.choices(available, weights=[weights[p] for p in available])[0]
        selected.append(pitch)
        available.remove(pitch)

    ratings = {}
    for pitch in selected:
        if pitch == "fb":
            ratings[pitch] = bounded_rating(40, 99)
        else:
            ratings[pitch] = bounded_rating(20, 95)

    for p in PITCH_LIST:
        ratings.setdefault(p, 0)

    potentials = {
        f"pot_{p}": bounded_potential(ratings[p], age) if ratings[p] else 0
        for p in PITCH_LIST
    }
    return ratings, potentials


def _maybe_add_hitting(player: Dict, age: int, allocation: float = 0.75) -> None:
    """Occasionally give a pitcher credible hitting attributes.

    According to the ARR tables there is a 1 in 100 chance that a pitcher is
    also a good hitter.  When triggered we allocate ``allocation`` percent of
    the usual rating points to hitting related attributes.
    """

    if random.randint(1, 100) != 1:
        return

    attrs = {}
    for key in ["ch", "ph", "sp", "gf", "pl", "vl", "sc"]:
        rating = int(bounded_rating() * allocation)
        attrs[key] = rating
        if key in {"ch", "ph", "sp", "gf", "sc"}:
            attrs[f"pot_{key}"] = bounded_potential(rating, age)

    player.update(attrs)


def _maybe_add_pitching(player: Dict, age: int, throws: str, allocation: float = 0.75) -> None:
    """Occasionally give a position player credible pitching attributes."""

    if random.randint(1, 1000) != 1:
        return

    endurance = _adjust_endurance(int(bounded_rating() * allocation))
    control = int(bounded_rating() * allocation)
    movement = int(bounded_rating() * allocation)
    hold_runner = int(bounded_rating() * allocation)
    delivery = random.choices(["overhand", "sidearm"], weights=[95, 5])[0]

    pitch_ratings, _ = generate_pitches(throws, delivery, age)
    pitch_ratings = {p: int(r * allocation) for p, r in pitch_ratings.items()}
    pitch_pots = {
        f"pot_{p}": bounded_potential(pitch_ratings[p], age) if pitch_ratings[p] else 0
        for p in PITCH_LIST
    }

    player.update(
        {
            "endurance": endurance,
            "control": control,
            "movement": movement,
            "hold_runner": hold_runner,
            "role": "SP" if endurance > 55 else "RP",
            "delivery": delivery,
            "pot_endurance": bounded_potential(endurance, age),
            "pot_control": bounded_potential(control, age),
            "pot_movement": bounded_potential(movement, age),
            "pot_hold_runner": bounded_potential(hold_runner, age),
        }
    )
    player.update(pitch_ratings)
    player.update(pitch_pots)
    for key in list(pitch_ratings.keys()) + list(pitch_pots.keys()):
        player.setdefault(key, 0)
    player.setdefault("other_positions", [])
    if "P" not in player["other_positions"]:
        player["other_positions"].append("P")

def generate_player(
    is_pitcher: bool,
    for_draft: bool = False,
    age_range: Optional[Tuple[int, int]] = None,
    primary_position: Optional[str] = None,
    player_type: Optional[str] = None,
) -> Dict:
    """Generate a single player record.

    Parameters
    ----------
    is_pitcher: bool
        If True a pitcher is created, otherwise a hitter.
    for_draft: bool
        When generating players for the draft pool the typical age range is
        narrower.  This flag preserves that behaviour when ``age_range`` is not
        supplied.
    age_range: Optional[Tuple[int, int]]
        Optional ``(min_age, max_age)`` tuple.  If provided it is forwarded to
        :func:`generate_birthdate` and takes precedence over ``player_type``.
    primary_position: Optional[str]
        When generating hitters this can be used to force a specific primary
        position rather than selecting one at random.
    player_type: Optional[str]
        Explicit player type to select the age table from
        :data:`AGE_TABLES`.  If not supplied ``for_draft`` determines whether
        the ``"amateur"`` or ``"fictional"`` table is used.

    Returns
    -------
    Dict
        A dictionary describing the generated player.
    """

    # Determine the player's age using either an explicit ``age_range`` or the
    # appropriate age table based on ``player_type``/``for_draft``.
    if age_range is not None:
        birthdate, age = generate_birthdate(age_range=age_range)
    else:
        if player_type is None:
            player_type = "amateur" if for_draft else "fictional"
        birthdate, age = generate_birthdate(player_type=player_type)
    first_name, last_name, ethnicity = generate_name()
    player_id = f"P{random.randint(1000, 9999)}"
    height = random.randint(68, 78)
    weight = random.randint(160, 250)
    skin_tone = assign_skin_tone(ethnicity)
    hair_color = assign_hair_color(ethnicity)
    facial_hair = assign_facial_hair(ethnicity, age)

    # Situational modifiers derived from ARR tables (lines 199-225)
    mo = roll_dice(35, 5, 5)  # monthly
    gf = roll_dice(25, 10, 4)  # ground/fly
    cl = roll_dice(35, 5, 5)  # close/late
    hm = roll_dice(35, 5, 5)  # home
    sc = roll_dice(35, 5, 5)  # scoring position
    # Widen pull rating distribution for greater variance
    pl = roll_dice(25, 5, 10)  # pull rating

    if is_pitcher:
        bats, throws = assign_bats_throws("P")
        # Expand pitcher platoon splits for more variation
        vl = roll_dice(20, 10, 6) if throws == "L" else roll_dice(10, 10, 6)
        # Allocate pitching related ratings from a shared pool using the ARR
        # derived weights.  A second pool is used to determine the pitcher's
        # fielding ability.
        core_ratings = _generate_pitcher_core_ratings(throws)
        endurance = core_ratings["endurance"]
        control = core_ratings["control"]
        movement = core_ratings["movement"]
        hold_runner = core_ratings["hold_runner"]
        arm = core_ratings["arm"]
        fa = core_ratings["fa"]

        role = "SP" if endurance > 55 else "RP"
        delivery = random.choices(["overhand", "sidearm"], weights=[95, 5])[0]
        pitch_ratings, pitch_pots = generate_pitches(throws, delivery, age)

        player = {
            "first_name": first_name,
            "last_name": last_name,
            "injured": 0,
            "injury_description": 0,
            "return_date": 0,
            "player_id": player_id,
            "is_pitcher": True,
            "birthdate": birthdate,
            "bats": bats,
            "throws": throws,
            "arm": arm,
            "fa": fa,
            "control": control,
            "movement": movement,
            "endurance": endurance,
            "hold_runner": hold_runner,
            "role": role,
            "delivery": delivery,
            "mo": mo,
            "gf": gf,
            "cl": cl,
            "hm": hm,
            "pl": pl,
            "vl": vl,
            "height": height,
            "weight": weight,
            "ethnicity": ethnicity,
            "skin_tone": skin_tone,
            "hair_color": hair_color,
            "facial_hair": facial_hair,
            "primary_position": "P",
            "other_positions": assign_secondary_positions("P"),
            "pot_control": bounded_potential(control, age),
            "pot_movement": bounded_potential(movement, age),
            "pot_endurance": bounded_potential(endurance, age),
            "pot_hold_runner": bounded_potential(hold_runner, age),
            "pot_arm": bounded_potential(arm, age),
            "pot_fa": bounded_potential(fa, age),
        }
        player.update(pitch_ratings)
        player.update(pitch_pots)
        for key in list(pitch_ratings.keys()) + list(pitch_pots.keys()):
            player.setdefault(key, 0)
        _maybe_add_hitting(player, age)
        player["pot_fielding"] = generate_fielding_potentials("P", player["other_positions"])
        return player

    else:
        # If the caller specifies a primary position we honour it and bypass
        # the usual random assignment.
        primary_pos = primary_position or assign_primary_position()
        bats, throws = assign_bats_throws(primary_pos)
        if bats == "L":
            vl = roll_dice(15, 10, 6)
        elif bats == "R":
            vl = roll_dice(20, 10, 6)
        else:
            vl = roll_dice(18, 10, 6)
        other_pos = assign_secondary_positions(primary_pos)
        ratings = _generate_hitter_ratings(primary_pos)
        ch = ratings["ch"]
        ph = ratings["ph"]
        sp = ratings["sp"]
        fa = ratings["fa"]
        arm = ratings["arm"]

        player = {
            "first_name": first_name,
            "last_name": last_name,
            "injured": 0,
            "injury_description": 0,
            "return_date": 0,
            "player_id": player_id,
            "is_pitcher": False,
            "birthdate": birthdate,
            "bats": bats,
            "throws": throws,
            "ch": ch,
            "ph": ph,
            "sp": sp,
            "gf": gf,
            "pl": pl,
            "vl": vl,
            "sc": sc,
            "mo": mo,
            "cl": cl,
            "hm": hm,
            "fa": fa,
            "arm": arm,
            "height": height,
            "weight": weight,
            "ethnicity": ethnicity,
            "skin_tone": skin_tone,
            "hair_color": hair_color,
            "facial_hair": facial_hair,
            "primary_position": primary_pos,
            "other_positions": other_pos,
            "pot_ch": bounded_potential(ch, age),
            "pot_ph": bounded_potential(ph, age),
            "pot_sp": bounded_potential(sp, age),
            "pot_fa": bounded_potential(fa, age),
            "pot_arm": bounded_potential(arm, age),
            "pot_sc": sc,
            "pot_gf": gf
        }
        all_keys = [
            "ch",
            "ph",
            "sp",
            "gf",
            "pl",
            "vl",
            "sc",
            "fa",
            "arm",
            "pot_ch",
            "pot_ph",
            "pot_sp",
            "pot_fa",
            "pot_arm",
            "pot_sc",
            "pot_gf",
        ]
        for key in all_keys:
            player.setdefault(key, 0)
        _maybe_add_pitching(player, age, throws)
        player["pot_fielding"] = generate_fielding_potentials(primary_pos, player["other_positions"])
        return player


def generate_draft_pool(num_players: int = 75) -> List[Dict]:
    players = []
    hitter_weight = sum(PRIMARY_POSITION_WEIGHTS.values())
    pitcher_weight = hitter_weight * (PITCHER_RATE / (1 - PITCHER_RATE))
    # Derive pitcher probability from position weights
    pitcher_rate = pitcher_weight / (pitcher_weight + hitter_weight)
    for _ in range(num_players):
        is_pitcher = random.random() < pitcher_rate
        players.append(generate_player(is_pitcher=is_pitcher, for_draft=True))
    # Ensure all players have all keys filled
    all_keys = set(k for player in players for k in player.keys())
    for player in players:
        for key in all_keys:
            player.setdefault(key, 0)

    return players

if __name__ == "__main__":  # pragma: no cover - manual script usage
    if pd is None:
        raise SystemExit("pandas is required to export the draft pool")
    draft_pool = generate_draft_pool()
    df = pd.DataFrame(draft_pool)
    df.to_csv("draft_pool.csv", index=False)
    print(f"Draft pool of {len(draft_pool)} players saved to draft_pool.csv")
