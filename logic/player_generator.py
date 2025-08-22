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


def _load_name_pool() -> Dict[str, List[Tuple[str, str]]]:
    pool: Dict[str, List[Tuple[str, str]]] = {}
    if NAME_PATH.exists():
        with NAME_PATH.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pool.setdefault(row["ethnicity"], []).append(
                    (row["first_name"], row["last_name"])
                )
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

def generate_name() -> tuple[str, str]:
    if name_pool:
        total_names = sum(len(v) for v in name_pool.values())
        if len(used_names) >= total_names:
            return "John", "Doe"
        while True:
            ethnicity = random.choice(list(name_pool.keys()))
            name = random.choice(name_pool[ethnicity])
            if name not in used_names:
                used_names.add(name)
                return name
    return "John", "Doe"


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
    "P": {"ch": 20, "ph": 127, "sp": 393, "fa": 557, "arm": 0},
    "C": {"ch": 169, "ph": 183, "sp": 166, "fa": 214, "arm": 269},
    "1B": {"ch": 193, "ph": 198, "sp": 163, "fa": 226, "arm": 221},
    "2B": {"ch": 180, "ph": 155, "sp": 206, "fa": 220, "arm": 239},
    "SS": {"ch": 167, "ph": 153, "sp": 199, "fa": 225, "arm": 256},
    "3B": {"ch": 181, "ph": 182, "sp": 175, "fa": 221, "arm": 240},
    "LF": {"ch": 175, "ph": 185, "sp": 202, "fa": 218, "arm": 220},
    "CF": {"ch": 182, "ph": 164, "sp": 235, "fa": 206, "arm": 213},
    "RF": {"ch": 173, "ph": 195, "sp": 187, "fa": 212, "arm": 233},
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

SKIN_TONE_WEIGHTS = {"dark": 25, "medium": 25, "light": 25}


def assign_primary_position() -> str:
    """Select a primary position using weights from the ARR tables."""
    return random.choices(
        list(PRIMARY_POSITION_WEIGHTS.keys()),
        weights=PRIMARY_POSITION_WEIGHTS.values(),
    )[0]


def assign_skin_tone() -> str:
    """Select a skin tone using weights from the ARR tables."""
    return random.choices(
        list(SKIN_TONE_WEIGHTS.keys()),
        weights=SKIN_TONE_WEIGHTS.values(),
    )[0]


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
    weights = PITCH_WEIGHTS[(throws, delivery)]
    total = random.randint(10 * len(PITCH_LIST), 99 * len(PITCH_LIST)) + 60
    num_pitches = max(2, min(5, total // 55))

    selected = ["fb"]
    available = weights.copy()
    available.pop("fb", None)
    for _ in range(num_pitches - 1):
        pitch = _weighted_choice(available)
        selected.append(pitch)
        available.pop(pitch, None)

    dist_weights = {p: weights[p] for p in selected}
    allocations = distribute_rating_points(total, dist_weights)
    ratings = {p: allocations.get(p, 0) for p in PITCH_LIST}
    potentials = {
        f"pot_{p}": bounded_potential(ratings[p], age) if p in selected else 0
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
    first_name, last_name = generate_name()
    player_id = f"P{random.randint(1000, 9999)}"
    height = random.randint(68, 78)
    weight = random.randint(160, 250)
    skin_tone = assign_skin_tone()

    # Situational modifiers derived from ARR tables (lines 199-225)
    mo = roll_dice(35, 5, 5)  # monthly
    gf = roll_dice(25, 10, 4)  # ground/fly
    cl = roll_dice(35, 5, 5)  # close/late
    hm = roll_dice(35, 5, 5)  # home
    sc = roll_dice(35, 5, 5)  # scoring position
    pl = roll_dice(35, 5, 5)  # pull rating

    if is_pitcher:
        bats, throws = assign_bats_throws("P")
        vl = roll_dice(30, 10, 4) if throws == "L" else roll_dice(20, 10, 4)
        # Allocate pitching related ratings from a shared pool using the ARR
        # derived weights.  A second pool is used to determine the pitcher's
        # fielding ability.
        pitch_pool = random.randint(
            10 * len(PITCHER_RATING_WEIGHTS),
            99 * len(PITCHER_RATING_WEIGHTS),
        )
        pitch_attrs = distribute_rating_points(pitch_pool, PITCHER_RATING_WEIGHTS)

        field_pool = random.randint(
            10 * len(HITTER_RATING_WEIGHTS["P"]),
            99 * len(HITTER_RATING_WEIGHTS["P"]),
        )
        field_attrs = distribute_rating_points(field_pool, HITTER_RATING_WEIGHTS["P"])

        endurance = _adjust_endurance(pitch_attrs["endurance"])
        control = pitch_attrs["control"]
        movement = pitch_attrs["movement"]
        if throws == "L":
            # Left-handed pitchers gain movement at the expense of control.
            movement = min(90, movement + 10)
            control = max(50, control - 10)
        hold_runner = pitch_attrs["hold_runner"]
        arm = pitch_attrs["arm"]
        fa = field_attrs["fa"]

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
            "skin_tone": skin_tone,
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
            vl = roll_dice(20, 10, 4)
        elif bats == "R":
            vl = roll_dice(30, 10, 4)
        else:
            vl = roll_dice(25, 10, 4)
        other_pos = assign_secondary_positions(primary_pos)
        pool = random.randint(
            10 * len(HITTER_RATING_WEIGHTS[primary_pos]),
            99 * len(HITTER_RATING_WEIGHTS[primary_pos]),
        )
        attr = distribute_rating_points(pool, HITTER_RATING_WEIGHTS[primary_pos])
        ch = attr["ch"]
        ph = attr["ph"]
        sp = attr["sp"]
        fa = attr["fa"]
        arm = attr["arm"]

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
            "skin_tone": skin_tone,
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
