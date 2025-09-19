import csv
from pathlib import Path
from functools import lru_cache

from models.player import Player
from models.pitcher import Pitcher
from utils.path_utils import get_base_dir
from utils.stats_persistence import load_stats


def _required_int(row, key):
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required field: {key}")
    return int(value)


def _optional_int(row, key, default=0):
    value = row.get(key)
    if value is None or value == "":
        return default
    return int(value)


@lru_cache(maxsize=None)
def load_players_from_csv(file_path):
    """Load player objects from a CSV file.

    Parameters
    ----------
    file_path : str or Path
        Path to the CSV file. Relative paths are resolved with respect to the
        project root so that callers can load data regardless of the current
        working directory.
    """

    file_path = str(file_path)
    base_path = get_base_dir()
    csv_path = Path(file_path)
    if not csv_path.is_absolute():
        csv_path = base_path / csv_path

    players = []
    with csv_path.open(mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            is_pitcher_value = row.get("is_pitcher", "").strip().lower()
            is_pitcher = is_pitcher_value in {"true", "1", "yes"}

            height = _required_int(row, "height")
            weight = _required_int(row, "weight")
            gf = _required_int(row, "gf")

            common_kwargs = {
                "player_id": row["player_id"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "birthdate": row["birthdate"],
                "height": height,
                "weight": weight,
                "ethnicity": row.get("ethnicity", ""),
                "skin_tone": row.get("skin_tone", ""),
                "hair_color": row.get("hair_color", ""),
                "facial_hair": row.get("facial_hair", ""),
                "bats": row["bats"],
                "primary_position": row["primary_position"],
                "other_positions": row.get("other_positions", "").split("|") if row.get("other_positions") else [],
                "gf": gf,
                "injured": (row.get("injured") or "false").strip().lower() == "true",
                "injury_description": row.get("injury_description") or None,
                "return_date": row.get("return_date") or None,
            }

            if is_pitcher:
                endurance = _required_int(row, "endurance")
                control = _required_int(row, "control")
                movement = _required_int(row, "movement")
                hold_runner = _required_int(row, "hold_runner")
                role = row.get("role", "")
                fb = _required_int(row, "fb")
                cu = _required_int(row, "cu")
                cb = _required_int(row, "cb")
                sl = _required_int(row, "sl")
                si = _required_int(row, "si")
                scb = _required_int(row, "scb")
                kn = _required_int(row, "kn")
                arm = _optional_int(row, "arm")
                if arm == 0:
                    arm = fb
                fa = _optional_int(row, "fa")
                player = Pitcher(
                    **common_kwargs,
                    endurance=endurance,
                    control=control,
                    movement=movement,
                    hold_runner=hold_runner,
                    fb=fb,
                    cu=cu,
                    cb=cb,
                    sl=sl,
                    si=si,
                    scb=scb,
                    kn=kn,
                    role=role,
                    arm=arm,
                    fa=fa,
                    potential={
                        "gf": _optional_int(row, "pot_gf", gf),
                        "fb": _optional_int(row, "pot_fb", fb),
                        "cu": _optional_int(row, "pot_cu", cu),
                        "cb": _optional_int(row, "pot_cb", cb),
                        "sl": _optional_int(row, "pot_sl", sl),
                        "si": _optional_int(row, "pot_si", si),
                        "scb": _optional_int(row, "pot_scb", scb),
                        "kn": _optional_int(row, "pot_kn", kn),
                        "control": _optional_int(row, "pot_control", control),
                        "movement": _optional_int(row, "pot_movement", movement),
                        "endurance": _optional_int(row, "pot_endurance", endurance),
                        "hold_runner": _optional_int(row, "pot_hold_runner", hold_runner),
                        "arm": _optional_int(row, "pot_arm", arm),
                        "fa": _optional_int(row, "pot_fa", fa),
                    },
                )
                player.is_pitcher = True
            else:
                ch = _required_int(row, "ch")
                ph = _required_int(row, "ph")
                sp = _required_int(row, "sp")
                pl = _required_int(row, "pl")
                vl = _required_int(row, "vl")
                sc = _required_int(row, "sc")
                fa = _required_int(row, "fa")
                arm = _required_int(row, "arm")
                player = Player(
                    **common_kwargs,
                    ch=ch,
                    ph=ph,
                    sp=sp,
                    pl=pl,
                    vl=vl,
                    sc=sc,
                    fa=fa,
                    arm=arm,
                    potential={
                        "ch": _optional_int(row, "pot_ch", ch),
                        "ph": _optional_int(row, "pot_ph", ph),
                        "sp": _optional_int(row, "pot_sp", sp),
                        "gf": _optional_int(row, "pot_gf", gf),
                        "pl": _optional_int(row, "pot_pl", pl),
                        "vl": _optional_int(row, "pot_vl", vl),
                        "sc": _optional_int(row, "pot_sc", sc),
                        "fa": _optional_int(row, "pot_fa", fa),
                        "arm": _optional_int(row, "pot_arm", arm),
                    },
                )
                player.is_pitcher = False

            players.append(player)
    stats = load_stats()
    for player in players:
        season = stats["players"].get(player.player_id)
        if season:
            player.season_stats = season
    return players
