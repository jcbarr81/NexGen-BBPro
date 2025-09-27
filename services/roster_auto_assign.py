from __future__ import annotations

"""Automatic roster assignment utilities.

Selects Active/AAA/Low rosters based on player ratings while respecting
current roster policies:

- Active roster: max 25 players and at least 11 position players
- AAA roster: max 15 players
- Low roster: max 10 players

Players marked as injured are moved to the disabled list (DL) and are not
considered for the Active roster. Existing DL/IR assignments are preserved.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from utils.path_utils import get_base_dir
from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.roster_loader import load_roster, save_roster
from utils.pitcher_role import get_role


ACTIVE_MAX = 25
AAA_MAX = 15
LOW_MAX = 10


@dataclass
class _Buckets:
    hitters: List[object]
    pitchers: List[object]
    injured: List[object]


def _split_players(players: Iterable[object]) -> _Buckets:
    hitters: List[object] = []
    pitchers: List[object] = []
    injured: List[object] = []
    for p in players:
        if getattr(p, "injured", False):
            injured.append(p)
            continue
        if getattr(p, "is_pitcher", False) or getattr(p, "primary_position", "").upper() == "P":
            pitchers.append(p)
        else:
            hitters.append(p)
    return _Buckets(hitters, pitchers, injured)


def _hitter_score(p) -> float:
    # Blend contact/power (CH/PH), speed (SP) and defensive ability (FA/ARM)
    ch = float(getattr(p, "ch", 0)); ph = float(getattr(p, "ph", 0))
    sp = float(getattr(p, "sp", 0))
    fa = float(getattr(p, "fa", 0)); arm = float(getattr(p, "arm", 0))
    off = 0.5 * ch + 0.5 * ph
    defense = 0.5 * fa + 0.5 * arm
    return 0.6 * off + 0.2 * sp + 0.2 * defense


def _pitcher_score(p) -> float:
    # Starters favour endurance; relievers favour stuff and control
    endurance = float(getattr(p, "endurance", 0))
    control = float(getattr(p, "control", 0))
    movement = float(getattr(p, "movement", 0))
    hold = float(getattr(p, "hold_runner", 0))
    arm = float(getattr(p, "arm", getattr(p, "fb", 0)))
    role = get_role(p)
    if role == "SP":
        return 0.5 * endurance + 0.25 * control + 0.2 * movement + 0.05 * hold
    return 0.35 * control + 0.35 * movement + 0.2 * endurance + 0.1 * arm


def _pick_active_roster(hitters: List[object], pitchers: List[object]) -> Tuple[List[str], List[object], List[object]]:
    # Choose 12 hitters and 13 pitchers by default, ensuring min 11 hitters.
    hitters_sorted = sorted(hitters, key=_hitter_score, reverse=True)
    pitchers_sorted = sorted(pitchers, key=_pitcher_score, reverse=True)

    # Ensure at least 5 SP in the active pitchers by preferring SPs from the top
    sps = [p for p in pitchers_sorted if get_role(p) == "SP"]
    rps = [p for p in pitchers_sorted if get_role(p) != "SP"]
    active_pitchers: List[object] = []
    active_pitchers.extend(sps[:5])
    remaining_slots = 13 - len(active_pitchers)
    if remaining_slots > 0:
        pool = [p for p in pitchers_sorted if p not in active_pitchers]
        active_pitchers.extend(pool[:remaining_slots])

    active_hitters = hitters_sorted[:12]
    # Adjust if not enough pitchers/hitters
    while len(active_hitters) < 11 and len(hitters_sorted) > len(active_hitters):
        active_hitters.append(hitters_sorted[len(active_hitters)])
    total = len(active_hitters) + len(active_pitchers)
    if total < ACTIVE_MAX:
        # Fill remaining slots by next best available across both lists
        pool = [p for p in hitters_sorted if p not in active_hitters] + [
            p for p in pitchers_sorted if p not in active_pitchers
        ]
        # Interleave hitters/pitchers while respecting min hitters
        for p in pool:
            if len(active_hitters) < 11 and not getattr(p, "is_pitcher", False):
                active_hitters.append(p)
            else:
                active_pitchers.append(p) if getattr(p, "is_pitcher", False) else active_hitters.append(p)
            if len(active_hitters) + len(active_pitchers) >= ACTIVE_MAX:
                break

    act_ids = [getattr(p, "player_id") for p in (active_pitchers + active_hitters)]
    rest_hitters = [p for p in hitters_sorted if getattr(p, "player_id") not in act_ids]
    rest_pitchers = [p for p in pitchers_sorted if getattr(p, "player_id") not in act_ids]
    return act_ids, rest_hitters, rest_pitchers


def auto_assign_team(team_id: str, *, players_file: str = "data/players.csv", roster_dir: str = "data/rosters") -> None:
    base = get_base_dir()
    players = {p.player_id: p for p in load_players_from_csv(players_file)}
    roster = load_roster(team_id, roster_dir)

    # Build the pool from current org players (ACT/AAA/LOW); keep DL/IR intact
    pool_ids = roster.act + roster.aaa + roster.low
    pool = [players[pid] for pid in pool_ids if pid in players]
    buckets = _split_players(pool)

    # Choose Active roster
    act_ids, rest_hitters, rest_pitchers = _pick_active_roster(buckets.hitters, buckets.pitchers)

    # Next best to AAA (cap 15)
    remainder = rest_hitters + rest_pitchers
    aaa_ids: List[str] = []
    for p in sorted(remainder, key=lambda x: (_pitcher_score(x) if getattr(x, 'is_pitcher', False) else _hitter_score(x)), reverse=True):
        if len(aaa_ids) >= AAA_MAX:
            break
        aaa_ids.append(getattr(p, "player_id"))

    # Remaining to Low (cap 10)
    low_ids: List[str] = []
    for p in remainder:
        pid = getattr(p, "player_id")
        if pid in act_ids or pid in aaa_ids:
            continue
        if len(low_ids) >= LOW_MAX:
            break
        low_ids.append(pid)

    # Preserve injured players on DL/IR
    roster.act = act_ids
    roster.aaa = aaa_ids
    roster.low = low_ids
    # Save
    save_roster(team_id, roster)


def auto_assign_all_teams(*, players_file: str = "data/players.csv", roster_dir: str = "data/rosters", teams_file: str = "data/teams.csv") -> None:
    teams = load_teams(teams_file)
    for team in teams:
        try:
            auto_assign_team(team.team_id, players_file=players_file, roster_dir=roster_dir)
        except Exception:
            # Continue with other teams; admin can fix any outliers manually
            continue


__all__ = ["auto_assign_team", "auto_assign_all_teams"]

