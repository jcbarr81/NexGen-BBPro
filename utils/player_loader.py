import csv
from models.player import Player
from models.pitcher import Pitcher


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


def load_players_from_csv(file_path):
    players = []
    with open(file_path, mode="r", newline="") as csvfile:
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

            players.append(player)
    return players
