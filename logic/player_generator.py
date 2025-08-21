# ARR-inspired Player Generator Script
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set, Optional
import csv
from pathlib import Path

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


def reset_name_cache():
    global name_pool, used_names
    name_pool = _load_name_pool()
    used_names = set()

    
# Helper Functions

def generate_birthdate(age_range=(18, 38)):
    today = datetime.today()
    age = random.randint(*age_range)
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

PITCHER_RATE = 0.4  # Fraction of draft pool that should be pitchers


def assign_primary_position() -> str:
    """Select a primary position using weights from the ARR tables."""
    return random.choices(
        list(PRIMARY_POSITION_WEIGHTS.keys()),
        weights=PRIMARY_POSITION_WEIGHTS.values(),
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
    weights = PITCH_WEIGHTS[(throws, delivery)].copy()
    num_pitches = random.randint(2, 5)
    selected = ["fb"]
    weights.pop("fb", None)
    for _ in range(num_pitches - 1):
        pitch = _weighted_choice(weights)
        selected.append(pitch)
        weights.pop(pitch, None)

    ratings = {p: bounded_rating() if p in selected else 0 for p in PITCH_LIST}
    potentials = {f"pot_{p}": bounded_potential(ratings[p], age) if p in selected else 0 for p in PITCH_LIST}
    return ratings, potentials

def generate_player(
    is_pitcher: bool,
    for_draft: bool = False,
    age_range: Optional[Tuple[int, int]] = None,
    primary_position: Optional[str] = None,
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
        :func:`generate_birthdate`.
    primary_position: Optional[str]
        When generating hitters this can be used to force a specific primary
        position rather than selecting one at random.

    Returns
    -------
    Dict
        A dictionary describing the generated player.
    """

    # Determine the effective age range for the player and pass it directly to
    # ``generate_birthdate``.  This allows callers to override the default
    # ranges used for draft or regular players.
    effective_age_range = age_range or ((17, 21) if for_draft else (18, 38))
    birthdate, age = generate_birthdate(effective_age_range)
    first_name, last_name = generate_name()
    player_id = f"P{random.randint(1000, 9999)}"
    height = random.randint(68, 78)
    weight = random.randint(160, 250)

    if is_pitcher:
        bats, throws = assign_bats_throws("P")
        endurance = bounded_rating()
        role = "SP" if endurance > 55 else "RP"
        delivery = random.choices(["overhand", "sidearm"], weights=[95, 5])[0]
        arm = bounded_rating()
        fa = bounded_rating()
        control = bounded_rating()
        movement = bounded_rating()
        hold_runner = bounded_rating()
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
            "height": height,
            "weight": weight,
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
        return player

    else:
        # If the caller specifies a primary position we honour it and bypass
        # the usual random assignment.
        primary_pos = primary_position or assign_primary_position()
        bats, throws = assign_bats_throws(primary_pos)
        other_pos = assign_secondary_positions(primary_pos)
        ch = bounded_rating()
        ph = bounded_rating()
        sp = bounded_rating()
        gf = bounded_rating()
        pl = bounded_rating()
        vl = bounded_rating()
        sc = bounded_rating()
        fa = bounded_rating()
        arm = bounded_rating()

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
            "fa": fa,
            "arm": arm,
            "height": height,
            "weight": weight,
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

if __name__ == "__main__":
    draft_pool = generate_draft_pool()
    df = pd.DataFrame(draft_pool)
    df.to_csv("draft_pool.csv", index=False)
    print(f"Draft pool of {len(draft_pool)} players saved to draft_pool.csv")
