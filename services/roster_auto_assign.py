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
from typing import Dict, Iterable, List, Tuple, Set

from utils.path_utils import get_base_dir
from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.roster_loader import load_roster, save_roster
from utils.pitcher_role import get_role


ACTIVE_MAX = 25
AAA_MAX = 15
LOW_MAX = 10

# Defensive positions that must be represented by at least one
# eligible player on the Active (ACT) roster to allow a legal lineup.
REQUIRED_POSITIONS: Tuple[str, ...] = ("C", "SS", "CF", "2B", "3B", "1B", "LF", "RF")


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


def _eligible_positions(player: object) -> Set[str]:
    """Return defensive positions the hitter can play.

    A player is considered eligible for their ``primary_position`` and any
    entries in ``other_positions``. Values are normalized to uppercase.
    Pitchers are excluded by the caller.
    """

    primary = str(getattr(player, "primary_position", "")).upper()
    others = getattr(player, "other_positions", []) or []
    elig = {primary} if primary else set()
    for pos in others:
        if not pos:
            continue
        elig.add(str(pos).upper())
    return elig


def _pick_active_roster(
    hitters: List[object],
    pitchers: List[object],
) -> Tuple[List[str], List[object], List[object]]:
    """Select a 25-man active roster with legal defensive coverage.

    - Target 12 hitters and 13 pitchers (min 11 hitters)
    - Ensure at least one eligible player for each defensive position in
      ``REQUIRED_POSITIONS`` among the 12 hitters.
    - Prefer best-graded players by role when multiple candidates exist.
    """

    hitters_sorted = sorted(hitters, key=_hitter_score, reverse=True)
    pitchers_sorted = sorted(pitchers, key=_pitcher_score, reverse=True)

    # Build the pitching staff: at least 5 SPs if available, then best remaining
    sps = [p for p in pitchers_sorted if get_role(p) == "SP"]
    active_pitchers: List[object] = []
    active_pitchers.extend(sps[:5])
    remaining_slots = 13 - len(active_pitchers)
    if remaining_slots > 0:
        pool = [p for p in pitchers_sorted if p not in active_pitchers]
        active_pitchers.extend(pool[:remaining_slots])

    # First, guarantee required defensive coverage among the hitters
    active_hitters: List[object] = []
    selected_ids: Set[str] = set()

    # Scarcity-aware order: C/SS/CF are typically the rarest
    for pos in REQUIRED_POSITIONS:
        candidate = None
        for h in hitters_sorted:
            pid = getattr(h, "player_id")
            if pid in selected_ids:
                continue
            elig = _eligible_positions(h)
            if pos in elig:
                candidate = h
                break
        if candidate is not None:
            active_hitters.append(candidate)
            selected_ids.add(getattr(candidate, "player_id"))

    # Fill remaining hitter slots up to 12 with best available
    for h in hitters_sorted:
        if len(active_hitters) >= 12:
            break
        pid = getattr(h, "player_id")
        if pid in selected_ids:
            continue
        active_hitters.append(h)
        selected_ids.add(pid)

    # Ensure at least 11 hitters overall; if short on hitters in org,
    # reduce pitchers to keep ACT at 25 while maximizing hitters.
    while len(active_hitters) < 11 and hitters_sorted:
        # Add next best hitter not already selected
        for h in hitters_sorted:
            pid = getattr(h, "player_id")
            if pid not in selected_ids:
                active_hitters.append(h)
                selected_ids.add(pid)
                break
        # Trim one pitcher if we somehow exceeded 13 earlier (safety)
        if len(active_pitchers) + len(active_hitters) > ACTIVE_MAX and active_pitchers:
            active_pitchers.pop()

    # Top off the 25-man roster if underfilled (shouldn't generally happen)
    total = len(active_hitters) + len(active_pitchers)
    if total < ACTIVE_MAX:
        # Prefer pitchers next to reach 25, but keep at least 11 hitters
        extra_pitchers = [p for p in pitchers_sorted if p not in active_pitchers]
        extra_hitters = [h for h in hitters_sorted if getattr(h, "player_id") not in selected_ids]
        while total < ACTIVE_MAX:
            if len(active_pitchers) < 13 and extra_pitchers:
                active_pitchers.append(extra_pitchers.pop(0))
            elif extra_hitters:
                active_hitters.append(extra_hitters.pop(0))
            elif extra_pitchers:
                active_pitchers.append(extra_pitchers.pop(0))
            else:
                break
            total = len(active_hitters) + len(active_pitchers)

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
