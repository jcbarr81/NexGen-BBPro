from __future__ import annotations

import random
from pathlib import Path
from typing import Dict

from utils.pitcher_role import get_role
from utils.player_loader import load_players_from_csv
from utils.roster_loader import load_roster, save_roster
from utils.team_loader import load_teams


def ensure_active_rosters(
    *,
    players: Dict[str, object] | None = None,
    players_file: str | Path = "data/players.csv",
    roster_dir: str | Path = "data/rosters",
    min_hitters: int = 9,
    min_pitchers: int = 1,
    active_max: int = 25,
) -> dict[str, int]:
    """Ensure each team has valid active players, filling from free agents if needed."""

    if players is None:
        players = {
            p.player_id: p for p in load_players_from_csv(str(players_file))
        }

    valid_ids = set(players.keys())
    rostered: set[str] = set()
    adjustments = 0

    rosters = {}
    for team in load_teams():
        roster = load_roster(team.team_id, roster_dir=roster_dir)
        removed = 0

        def _filter_ids(ids: list[str]) -> list[str]:
            nonlocal removed
            filtered = [pid for pid in ids if pid in valid_ids]
            removed += len(ids) - len(filtered)
            return filtered

        roster.act = _filter_ids(roster.act)
        roster.aaa = _filter_ids(roster.aaa)
        roster.low = _filter_ids(roster.low)
        roster.dl = _filter_ids(roster.dl)
        roster.ir = _filter_ids(roster.ir)
        if roster.dl_tiers:
            roster.dl_tiers = {
                pid: tier for pid, tier in roster.dl_tiers.items() if pid in valid_ids
            }
        if removed:
            adjustments += removed
        rosters[team.team_id] = roster
        rostered.update(roster.act + roster.aaa + roster.low + roster.dl + roster.ir)

    def is_pitcher(pid: str) -> bool:
        player = players.get(pid)
        if player is None:
            return False
        role = get_role(player)
        if role in {"SP", "RP"}:
            return True
        return bool(getattr(player, "is_pitcher", False)) or str(
            getattr(player, "primary_position", "")
        ).upper() in {"P", "SP", "RP"}

    free_agents = [
        pid
        for pid in players.keys()
        if pid not in rostered and not str(pid).startswith("D")
    ]
    random.shuffle(free_agents)
    free_hitters = [pid for pid in free_agents if not is_pitcher(pid)]
    free_pitchers = [pid for pid in free_agents if is_pitcher(pid)]

    for team_id, roster in rosters.items():
        act_ids = list(dict.fromkeys(roster.act))
        act_hitters = [pid for pid in act_ids if not is_pitcher(pid)]
        act_pitchers = [pid for pid in act_ids if is_pitcher(pid)]

        org_hitters = [
            pid
            for pid in (roster.aaa + roster.low)
            if not is_pitcher(pid) and pid not in act_ids
        ]
        org_pitchers = [
            pid
            for pid in (roster.aaa + roster.low)
            if is_pitcher(pid) and pid not in act_ids
        ]

        need_hitters = max(0, min_hitters - len(act_hitters))
        while need_hitters > 0:
            if org_hitters:
                pid = org_hitters.pop(0)
                if pid in roster.aaa:
                    roster.aaa.remove(pid)
                if pid in roster.low:
                    roster.low.remove(pid)
            elif free_hitters:
                pid = free_hitters.pop(0)
            else:
                break
            act_ids.append(pid)
            act_hitters.append(pid)
            need_hitters -= 1
            adjustments += 1

        while len(act_pitchers) < min_pitchers:
            if org_pitchers:
                pid = org_pitchers.pop(0)
                if pid in roster.aaa:
                    roster.aaa.remove(pid)
                if pid in roster.low:
                    roster.low.remove(pid)
                act_ids.append(pid)
                act_pitchers.append(pid)
                adjustments += 1
            elif free_pitchers:
                pid = free_pitchers.pop(0)
                act_ids.append(pid)
                act_pitchers.append(pid)
                adjustments += 1
            else:
                break

        def add_hitter() -> bool:
            if org_hitters:
                pid = org_hitters.pop()
                if pid in roster.aaa:
                    roster.aaa.remove(pid)
                if pid in roster.low:
                    roster.low.remove(pid)
            elif free_hitters:
                pid = free_hitters.pop()
            else:
                return False
            act_ids.append(pid)
            act_hitters.append(pid)
            return True

        def add_pitcher() -> bool:
            if org_pitchers:
                pid = org_pitchers.pop()
                if pid in roster.aaa:
                    roster.aaa.remove(pid)
                if pid in roster.low:
                    roster.low.remove(pid)
            elif free_pitchers:
                pid = free_pitchers.pop()
            else:
                return False
            act_ids.append(pid)
            act_pitchers.append(pid)
            return True

        target_hitters = max(min_hitters, 12)
        target_pitchers = max(min_pitchers, 13)
        while len(act_ids) < active_max:
            if len(act_hitters) < target_hitters and add_hitter():
                adjustments += 1
                continue
            if len(act_pitchers) < target_pitchers and add_pitcher():
                adjustments += 1
                continue
            if add_pitcher():
                adjustments += 1
                continue
            if add_hitter():
                adjustments += 1
                continue
            break

        while len(act_ids) > active_max and act_pitchers and len(act_pitchers) > min_pitchers:
            pid = act_pitchers.pop()
            if pid in act_ids:
                act_ids.remove(pid)

        while len(act_ids) > active_max and len(act_hitters) > min_hitters:
            pid = act_hitters.pop()
            if pid in act_ids:
                act_ids.remove(pid)

        roster.act = act_ids
        save_roster(team_id, roster)

    return {
        "adjustments": adjustments,
        "free_agents_left": len(free_hitters) + len(free_pitchers),
    }
