from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from utils.path_utils import get_base_dir
from utils.pitcher_recovery import PitcherRecoveryTracker
from utils.pitcher_role import get_role
from utils.sim_date import get_current_sim_date
from utils.standings_utils import normalize_record

DATE_FMT = "%Y-%m-%d"


@dataclass
class _ScheduleEntry:
    date: str
    home: str
    away: str
    result: str | None
    played: bool

    def opponent_for(self, team_id: str) -> str | None:
        if self.home == team_id:
            return self.away
        if self.away == team_id:
            return self.home
        return None

    def is_home_for(self, team_id: str) -> bool:
        return self.home == team_id


def gather_owner_quick_metrics(
    team_id: str,
    *,
    base_path: Path | None = None,
    roster: Any | None = None,
    players: Mapping[str, Any] | None = None,
    window: int = 12,
) -> Dict[str, Any]:
    """Collect lightweight metrics plus bullpen/matchup insights for owners."""

    base_dir = get_base_dir() if base_path is None else Path(base_path)
    data_dir = base_dir / "data"

    standings_path = data_dir / "standings.json"
    standings_raw = _load_json_dict(standings_path)
    standings_normalized = {
        key: normalize_record(value) for key, value in standings_raw.items()
    }
    team_standings = standings_normalized.get(team_id, {})

    schedule_path = data_dir / "schedule.csv"
    schedule_entries = _load_schedule(schedule_path)
    team_schedule = [entry for entry in schedule_entries if entry.opponent_for(team_id)]

    today = _current_date()
    next_game = _find_next_game(team_schedule, today)
    next_opponent, next_date = _describe_next_game(next_game, team_id)

    last_game_played = _find_last_game(team_schedule)
    trend_data = _collect_trend_data(
        team_id, base_dir, team_schedule, standings_normalized, window=window
    )

    injuries = _count_injuries(roster)
    probable_sp = _probable_starter_for_team(roster, players)

    bullpen = _compute_bullpen_readiness(team_id, base_dir, roster, players, today)
    if probable_sp and bullpen.get("probable_starter") in {None, "--"}:
        bullpen["probable_starter"] = probable_sp
    matchup = _build_matchup_scout(
        team_id,
        next_game,
        standings_normalized,
        bullpen.get("probable_starter"),
    )

    metrics = {
        "record": _format_record(team_standings),
        "run_diff": _format_run_diff(team_standings),
        "next_opponent": next_opponent,
        "next_date": next_date,
        "streak": _format_streak(team_standings),
        "last10": _format_last10(team_standings),
        "injuries": injuries,
        "prob_sp": probable_sp,
        "bullpen": bullpen,
        "matchup": matchup,
        "trends": trend_data,
        "last_game": last_game_played,
    }
    return metrics


# ---------------------------------------------------------------------------
# Standings helpers


def _format_record(standing: Mapping[str, Any]) -> str:
    if not standing:
        return "--"
    try:
        wins = int(standing.get("wins", standing.get("w", 0)) or 0)
        losses = int(standing.get("losses", standing.get("l", 0)) or 0)
        return f"{wins}-{losses}"
    except Exception:
        return "--"


def _format_run_diff(standing: Mapping[str, Any]) -> str:
    if not standing:
        return "--"
    try:
        runs_for = int(standing.get("runs_for", standing.get("r", 0)) or 0)
        runs_against = int(standing.get("runs_against", standing.get("ra", 0)) or 0)
        diff = runs_for - runs_against
        return f"{diff:+d}"
    except Exception:
        return "--"


def _format_streak(standing: Mapping[str, Any]) -> str:
    if not standing:
        return "--"
    streak = standing.get("streak", {})
    try:
        result = str(streak.get("result", "")).upper()
        length = int(streak.get("length", 0) or 0)
        if result in {"W", "L"} and length > 0:
            return f"{result}{length}"
    except Exception:
        pass
    return "--"


def _format_last10(standing: Mapping[str, Any]) -> str:
    if not standing:
        return "--"
    raw = standing.get("last10")
    if isinstance(raw, Sequence):
        wins = sum(1 for item in raw if str(item).upper().startswith("W"))
        losses = sum(1 for item in raw if str(item).upper().startswith("L"))
        if wins or losses:
            return f"{wins}-{losses}"
    return "--"


# ---------------------------------------------------------------------------
# Schedule loading


def _load_schedule(path: Path) -> List[_ScheduleEntry]:
    if not path.exists():
        return []
    entries: List[_ScheduleEntry] = []
    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                date_token = str(row.get("date") or "").strip()
                home = str(row.get("home") or "").strip()
                away = str(row.get("away") or "").strip()
                if not (date_token and home and away):
                    continue
                result = str(row.get("result") or "").strip() or None
                played_flag = str(row.get("played") or "").strip()
                played = played_flag == "1" or bool(result)
                entries.append(
                    _ScheduleEntry(
                        date=date_token,
                        home=home,
                        away=away,
                        result=result,
                        played=played,
                    )
                )
    except OSError:
        return []
    return entries


def _find_next_game(
    schedule: Sequence[_ScheduleEntry], today: date
) -> Optional[_ScheduleEntry]:
    for entry in schedule:
        if entry.played:
            continue
        entry_date = _parse_date(entry.date)
        if entry_date >= today:
            return entry
    # Fall back to first future game even if earlier dates missing
    for entry in schedule:
        if not entry.played:
            return entry
    return None


def _find_last_game(
    schedule: Sequence[_ScheduleEntry],
) -> Optional[Dict[str, Any]]:
    for entry in reversed(schedule):
        if entry.played:
            return {
                "date": entry.date,
                "home": entry.home,
                "away": entry.away,
                "result": entry.result,
            }
    return None


def _describe_next_game(
    next_game: Optional[_ScheduleEntry], team_id: str
) -> Tuple[str, str]:
    if next_game is None:
        return "--", "--"
    opponent = next_game.opponent_for(team_id) or "--"
    prefix = "vs " if next_game.is_home_for(team_id) else "at "
    return prefix + opponent, next_game.date


# ---------------------------------------------------------------------------
# Injuries and probable starters


def _count_injuries(roster: Any | None) -> int:
    if roster is None:
        return 0
    try:
        disabled = len(getattr(roster, "dl", []) or [])
        injured = len(getattr(roster, "ir", []) or [])
        return int(disabled + injured)
    except Exception:
        return 0


def _probable_starter_for_team(
    roster: Any | None,
    players: Mapping[str, Any] | None,
) -> str:
    if roster is None or not players:
        return "--"
    try:
        act_ids = set(getattr(roster, "act", []) or [])
        starters = []
        for pid in act_ids:
            player = players.get(pid)
            if player is None:
                continue
            role = getattr(player, "role", None) or get_role(player)
            if role == "SP":
                endurance = int(getattr(player, "endurance", 0) or 0)
                starters.append((endurance, player))
        if starters:
            starters.sort(key=lambda item: item[0], reverse=True)
            candidate = starters[0][1]
            return _format_player_name(candidate)
    except Exception:
        pass
    return "--"


# ---------------------------------------------------------------------------
# Bullpen readiness


def _compute_bullpen_readiness(
    team_id: str,
    base_dir: Path,
    roster: Any | None,
    players: Mapping[str, Any] | None,
    today: date,
) -> Dict[str, Any]:
    result = {
        "ready": 0,
        "limited": 0,
        "rest": 0,
        "total": 0,
        "detail": [],
        "headline": "--",
        "probable_starter": "--",
    }
    if roster is None or not players:
        return result

    try:
        tracker = PitcherRecoveryTracker.instance()
        tracker.ensure_team(
            team_id,
            base_dir / "data" / "players.csv",
            base_dir / "data" / "rosters",
        )
        entry = tracker.data.get("teams", {}).get(team_id, {})
        statuses = entry.get("pitchers", {}) or {}

        bullpen_ids = [
            pid
            for pid in getattr(roster, "act", []) or []
            if _is_bullpen_pitcher(players.get(pid))
        ]
        result["total"] = len(bullpen_ids)

        for pid in bullpen_ids:
            player = players.get(pid)
            status = statuses.get(pid, {})
            available_on = _parse_date(status.get("available_on"))
            last_used = status.get("last_used") or None
            last_pitches = int(status.get("last_pitches", 0) or 0)
            days = (available_on - today).days if available_on else 0
            if days <= 0:
                bucket = "ready"
                label = "Ready"
            elif days == 1:
                bucket = "limited"
                label = "Limited"
            else:
                bucket = "rest"
                label = f"Rest {days}d"
            result[bucket] = int(result[bucket]) + 1
            result["detail"].append(
                {
                    "player_id": pid,
                    "name": _format_player_name(player),
                    "status": label,
                    "days": days if days > 0 else 0,
                    "last_used": last_used,
                    "last_pitches": last_pitches,
                }
            )

        if result["total"]:
            result["headline"] = (
                f"{result['ready']} ready / "
                f"{result['limited']} limited / "
                f"{result['rest']} resting"
            )
    except Exception:
        pass

    return result


def _is_bullpen_pitcher(player: Any | None) -> bool:
    if player is None:
        return False
    role = getattr(player, "role", None) or get_role(player)
    if role == "SP":
        return False
    is_pitcher = bool(getattr(player, "is_pitcher", False))
    primary = str(getattr(player, "primary_position", "")).upper()
    return is_pitcher or primary in {"P", "RP", "CL"}


# ---------------------------------------------------------------------------
# Matchup scouting


def _build_matchup_scout(
    team_id: str,
    next_game: Optional[_ScheduleEntry],
    standings: Mapping[str, Mapping[str, Any]],
    probable_starter: str | None,
) -> Dict[str, Any]:
    if next_game is None:
        return {
            "opponent": "--",
            "venue": "--",
            "record": "--",
            "run_diff": "--",
            "streak": "--",
            "note": "No games remaining on the schedule.",
            "opponent_probable": "--",
            "team_probable": probable_starter or "--",
        }
    opponent = next_game.opponent_for(team_id) or "--"
    entry = standings.get(opponent, {})
    venue = "Home" if next_game.is_home_for(team_id) else "Road"
    return {
        "opponent": opponent,
        "venue": venue,
        "record": _format_record(entry),
        "run_diff": _format_run_diff(entry),
        "streak": _format_streak(entry),
        "note": _build_matchup_note(entry),
        "opponent_probable": "--",
        "team_probable": probable_starter or "--",
        "date": next_game.date,
    }


def _build_matchup_note(standing: Mapping[str, Any]) -> str:
    try:
        runs_for = int(standing.get("runs_for", standing.get("r", 0)) or 0)
        runs_against = int(standing.get("runs_against", standing.get("ra", 0)) or 0)
        games = int(standing.get("games_played", standing.get("g", 0)) or 0)
        if games <= 0:
            return "Limited opponent data."
        rpg = runs_for / games
        rapg = runs_against / games
        diff = rpg - rapg
        if diff >= 0.75:
            return "High-powered offense; expect a slugfest."
        if diff <= -0.5:
            return "Run prevention club; prioritize contact hitters."
        if rapg <= 3.5:
            return "Opponent bullpen trending strong; manufacture runs."
        return "Balanced opponent; leverage platoon advantages."
    except Exception:
        return "Opponent analytics unavailable."


# ---------------------------------------------------------------------------
# Trend data


def _collect_trend_data(
    team_id: str,
    base_dir: Path,
    schedule: Sequence[_ScheduleEntry],
    standings: Mapping[str, Mapping[str, Any]],
    *,
    window: int,
) -> Dict[str, Any]:
    history_dir = base_dir / "data" / "season_history"
    snapshots = sorted(history_dir.glob("*.json"))
    trend_points = []
    for path in snapshots[-max(window, 4) :]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        team_entry = payload.get("teams", {}).get(team_id)
        if not team_entry:
            continue
        games = int(team_entry.get("g", 0) or 0)
        wins = int(team_entry.get("w", 0) or 0)
        runs = float(team_entry.get("r", 0) or 0.0)
        runs_allowed = float(team_entry.get("ra", 0) or 0.0)
        rpg = runs / games if games else 0.0
        rapg = runs_allowed / games if games else 0.0
        win_pct = wins / games if games else 0.0
        trend_points.append(
            {
                "date": path.stem,
                "runs_per_game": round(rpg, 2),
                "runs_allowed_per_game": round(rapg, 2),
                "win_pct": round(win_pct, 3),
            }
        )
    if not trend_points:
        return {"series": [], "dates": []}
    dates = [p["date"] for p in trend_points]
    return {
        "dates": dates,
        "series": {
            "runs_per_game": [p["runs_per_game"] for p in trend_points],
            "runs_allowed_per_game": [
                p["runs_allowed_per_game"] for p in trend_points
            ],
            "win_pct": [p["win_pct"] for p in trend_points],
        },
    }


# ---------------------------------------------------------------------------
# Utilities


def _load_json_dict(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _current_date() -> date:
    sim_date = get_current_sim_date()
    if sim_date:
        try:
            return datetime.strptime(str(sim_date), DATE_FMT).date()
        except Exception:
            pass
    return datetime.utcnow().date()


def _parse_date(value: str | None) -> date:
    if not value:
        return datetime.utcnow().date()
    try:
        return datetime.strptime(value, DATE_FMT).date()
    except Exception:
        return datetime.utcnow().date()


def _format_player_name(player: Any | None) -> str:
    if player is None:
        return "--"
    first = str(getattr(player, "first_name", "")).strip()
    last = str(getattr(player, "last_name", "")).strip()
    full = " ".join(part for part in (first, last) if part)
    return full or str(getattr(player, "player_id", "--"))


__all__ = ["gather_owner_quick_metrics"]

