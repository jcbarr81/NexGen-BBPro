import colorsys
import csv
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from models.player import Player
from models.pitcher import Pitcher
from utils.player_writer import save_players_to_csv
from logic.player_generator import generate_player, reset_name_cache
from utils.user_manager import clear_users


def _abbr(city: str, name: str, existing: set) -> str:
    """Generate a unique team abbreviation based solely on the city name.

    The abbreviation uses the first three letters of the *city* and appends
    a number if necessary to ensure uniqueness. The *name* parameter is
    ignored but kept for backward compatibility with callers.
    """
    base = city[:3].upper()
    candidate = base
    i = 1
    while candidate in existing:
        candidate = f"{base}{i}"
        i += 1
    existing.add(candidate)
    return candidate


def _unique_color_pair(used: set) -> tuple[str, str]:
    """Generate a pair of contrasting hex colors not already in *used*.

    Colors are generated deterministically using evenly distributed hues. The
    secondary color is the complement of the primary. Both colors are added to
    *used* before returning.
    """
    idx = len(used) // 2
    while True:
        hue = (idx * 0.618033988749895) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.95)
        primary = f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

        comp_hue = (hue + 0.5) % 1.0
        r2, g2, b2 = colorsys.hsv_to_rgb(comp_hue, 0.6, 0.95)
        secondary = f"#{int(r2 * 255):02X}{int(g2 * 255):02X}{int(b2 * 255):02X}"

        if primary not in used and secondary not in used:
            used.update({primary, secondary})
            return primary, secondary
        idx += 1


def _dict_to_model(data: dict):
    potentials = {k[4:]: v for k, v in data.items() if k.startswith("pot_")}
    other_pos = data.get("other_positions")
    common = dict(
        player_id=data.get("player_id"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        birthdate=str(data.get("birthdate")),
        height=data.get("height", 0),
        weight=data.get("weight", 0),
        ethnicity=data.get("ethnicity", ""),
        skin_tone=data.get("skin_tone", ""),
        hair_color=data.get("hair_color", ""),
        facial_hair=data.get("facial_hair", ""),
        bats=data.get("bats", "R"),
        primary_position=data.get("primary_position", ""),
        other_positions=other_pos if isinstance(other_pos, list) else (other_pos.split("|") if other_pos else []),
        gf=data.get("gf", 0),
        injured=bool(data.get("injured", 0)),
        injury_description=data.get("injury_description"),
        return_date=data.get("return_date"),
    )
    if data.get("is_pitcher"):
        arm = data.get("arm") or data.get("fb", 0)
        potentials.setdefault("arm", arm)
        return Pitcher(
            **common,
            endurance=data.get("endurance", 0),
            control=data.get("control", 0),
            movement=data.get("movement", 0),
            hold_runner=data.get("hold_runner", 0),
            fb=data.get("fb", 0),
            cu=data.get("cu", 0),
            cb=data.get("cb", 0),
            sl=data.get("sl", 0),
            si=data.get("si", 0),
            scb=data.get("scb", 0),
            kn=data.get("kn", 0),
            arm=arm,
            fa=data.get("fa", 0),
            potential=potentials,
        )
    else:
        return Player(
            **common,
            ch=data.get("ch", 0),
            ph=data.get("ph", 0),
            sp=data.get("sp", 0),
            pl=data.get("pl", 0),
            vl=data.get("vl", 0),
            sc=data.get("sc", 0),
            fa=data.get("fa", 0),
            arm=data.get("arm", 0),
            potential=potentials,
        )


def _purge_old_league(base_dir: Path) -> None:
    """Remove remnants of a previous league from ``base_dir``.

    Static resources required for league generation are preserved. Player
    avatars reside outside ``base_dir`` and are therefore untouched.
    """
    keep = {"names.csv", "ballparks.py", "MLB_avg"}
    for item in base_dir.iterdir():
        if item.name in keep:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def _ensure_act_positions(players: List[dict]) -> None:
    """Ensure the active roster has coverage for all positions.

    Parameters
    ----------
    players:
        List of player dictionaries representing the ACT roster.

    Raises
    ------
    ValueError
        If any required position is missing from the roster.
    """
    required = {"P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"}
    positions = {p.get("primary_position") for p in players}
    missing = required - positions
    if missing:
        raise ValueError(
            "ACT roster missing positions: " + ", ".join(sorted(missing))
        )


def create_league(base_dir: str | Path, divisions: Dict[str, List[Tuple[str, str]]], league_name: str):
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    _purge_old_league(base_dir)
    reset_name_cache()
    rosters_dir = base_dir / "rosters"
    rosters_dir.mkdir(parents=True, exist_ok=True)

    clear_users()

    teams_path = base_dir / "teams.csv"
    players_path = base_dir / "players.csv"
    league_path = base_dir / "league.txt"

    team_rows = []
    all_players = []
    existing_abbr = set()
    used_colors: set[str] = set()

    def generate_roster(num_pitchers: int, num_hitters: int, age_range: Tuple[int, int], ensure_positions: bool = False):
        players = []
        for _ in range(num_pitchers):
            data = generate_player(is_pitcher=True, age_range=age_range)
            data["is_pitcher"] = True
            players.append(data)
        if ensure_positions:
            positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
            for pos in positions:
                data = generate_player(is_pitcher=False, age_range=age_range, primary_position=pos)
                data["is_pitcher"] = False
                players.append(data)
            remaining = num_hitters - len(positions)
        else:
            remaining = num_hitters
        for _ in range(remaining):
            data = generate_player(is_pitcher=False, age_range=age_range)
            data["is_pitcher"] = False
            players.append(data)
        return players

    for division, teams in divisions.items():
        for city, name in teams:
            abbr = _abbr(city, name, existing_abbr)
            primary, secondary = _unique_color_pair(used_colors)
            team_rows.append(
                {
                    "team_id": abbr,
                    "name": name,
                    "city": city,
                    "abbreviation": abbr,
                    "division": division,
                    "stadium": f"{name} Stadium",
                    "primary_color": primary,
                    "secondary_color": secondary,
                    "owner_id": "",
                }
            )

            act_players = generate_roster(11, 14, (21, 38), ensure_positions=True)
            _ensure_act_positions(act_players)
            aaa_players = generate_roster(7, 8, (21, 38))
            low_players = generate_roster(5, 5, (18, 21))

            roster_levels = {"ACT": act_players, "AAA": aaa_players, "LOW": low_players}

            for level_players in roster_levels.values():
                all_players.extend(level_players)

            roster_file = rosters_dir / f"{abbr}.csv"
            with roster_file.open("w", newline="") as f:
                writer = csv.writer(f)
                for level, players in roster_levels.items():
                    for p in players:
                        writer.writerow([p["player_id"], level])

    player_models = [_dict_to_model(p) for p in all_players]
    save_players_to_csv(player_models, players_path)

    with open(teams_path, "w", newline="") as f:
        fieldnames = [
            "team_id","name","city","abbreviation","division","stadium","primary_color","secondary_color","owner_id"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(team_rows)
    with open(league_path, "w", newline="") as f:
        f.write(league_name)
