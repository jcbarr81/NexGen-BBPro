from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from utils.path_utils import get_base_dir
from utils.pitcher_recovery import PitcherRecoveryTracker
from utils.pitcher_role import get_role
from utils.sim_date import get_current_sim_date
from utils.stats_persistence import load_stats as _load_season_stats
from services.standings_repository import load_standings
try:
    from playbalance.config import load_config as _load_playbalance_config
except Exception:  # pragma: no cover - optional dependency in some test harnesses
    _load_playbalance_config = None  # type: ignore

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

    standings_normalized = load_standings(base_path=data_dir)
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

    metrics["calibration"] = _calibration_summary(base_dir)

    (
        batting_leaders,
        pitching_leaders,
        leader_meta,
    ) = _collect_team_leaders(
        base_dir, roster, players
    )
    metrics["batting_leaders"] = batting_leaders
    metrics["pitching_leaders"] = pitching_leaders
    metrics["leader_meta"] = leader_meta
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
# Team leader helpers


def _collect_team_leaders(
    base_dir: Path,
    roster: Any | None,
    players: Mapping[str, Any] | None,
) -> tuple[Dict[str, str], Dict[str, str], Dict[str, Dict[str, Dict[str, Any]]]]:
    batting = {"avg": "--", "hr": "--", "rbi": "--"}
    pitching = {"wins": "--", "so": "--", "saves": "--"}
    meta: Dict[str, Dict[str, Dict[str, Any]]] = {"batting": {}, "pitching": {}}
    if roster is None or not players:
        return batting, pitching, meta

    candidate_ids: list[str] = []
    seen: set[str] = set()
    for attr in ("act", "dl", "ir"):
        try:
            ids = getattr(roster, attr, []) or []
        except Exception:
            ids = []
        for pid in ids:
            if not pid:
                continue
            pid_str = str(pid)
            if pid_str in seen:
                continue
            candidate_ids.append(pid_str)
            seen.add(pid_str)
    if not candidate_ids:
        return batting, pitching, meta

    try:
        stats_payload = _load_season_stats(base_dir / "data" / "season_stats.json")
    except Exception:
        stats_payload = {}
    raw_player_stats = (
        stats_payload.get("players", {}) if isinstance(stats_payload, Mapping) else {}
    )

    hitters: list[tuple[Any, Mapping[str, Any]]] = []
    pitchers: list[tuple[Any, Mapping[str, Any]]] = []
    for pid in candidate_ids:
        player = players.get(pid)
        if player is None:
            continue
        stats = raw_player_stats.get(pid, {})
        if not isinstance(stats, Mapping):
            stats = {}
        if not stats:
            local_stats = getattr(player, "season_stats", None)
            if isinstance(local_stats, Mapping):
                stats = local_stats
        if _is_pitcher_type(player):
            if _has_pitcher_sample(stats):
                pitchers.append((player, stats))
        else:
            if _has_batter_sample(stats):
                hitters.append((player, stats))

    avg_leader = _find_avg_leader(hitters)
    hr_leader = _find_stat_leader(hitters, ("hr", "HR"))
    rbi_leader = _find_stat_leader(hitters, ("rbi", "RBI"))
    win_leader = _find_stat_leader(pitchers, ("w", "wins", "W"))
    so_leader = _find_stat_leader(pitchers, ("so", "SO", "k", "K"))
    save_leader = _find_stat_leader(pitchers, ("sv", "SV", "saves", "S"))

    batting["avg"], meta_entry = _format_leader_entry(avg_leader, stat="avg")
    if meta_entry and meta_entry.get("player_id"):
        meta["batting"]["avg"] = meta_entry
    batting["hr"], meta_entry = _format_leader_entry(hr_leader, stat="int")
    if meta_entry and meta_entry.get("player_id"):
        meta["batting"]["hr"] = meta_entry
    batting["rbi"], meta_entry = _format_leader_entry(rbi_leader, stat="int")
    if meta_entry and meta_entry.get("player_id"):
        meta["batting"]["rbi"] = meta_entry

    pitching["wins"], meta_entry = _format_leader_entry(win_leader, stat="int")
    if meta_entry and meta_entry.get("player_id"):
        meta["pitching"]["wins"] = meta_entry
    pitching["so"], meta_entry = _format_leader_entry(so_leader, stat="int")
    if meta_entry and meta_entry.get("player_id"):
        meta["pitching"]["so"] = meta_entry
    pitching["saves"], meta_entry = _format_leader_entry(save_leader, stat="int")
    if meta_entry and meta_entry.get("player_id"):
        meta["pitching"]["saves"] = meta_entry

    return batting, pitching, meta


def _has_batter_sample(stats: Mapping[str, Any]) -> bool:
    ab = _safe_float(_first_value(stats, ("ab", "AB")))
    pa = _safe_float(_first_value(stats, ("pa", "PA")))
    sample = ab if ab is not None else pa
    return sample is not None and sample > 0


def _has_pitcher_sample(stats: Mapping[str, Any]) -> bool:
    outs = _safe_float(_first_value(stats, ("outs", "OUTS")))
    if outs is None:
        ip_val = _safe_float(_first_value(stats, ("ip", "IP")))
        if ip_val is not None:
            outs = ip_val * 3.0
    return outs is not None and outs > 0


def _find_avg_leader(
    hitters: Sequence[tuple[Any, Mapping[str, Any]]],
) -> Optional[tuple[Any, float]]:
    leader: Optional[tuple[Any, float]] = None
    for player, stats in hitters:
        avg_val = _safe_float(_first_value(stats, ("avg", "AVG")))
        if avg_val is None:
            hits = _safe_float(_first_value(stats, ("h", "H"))) or 0.0
            ab = _safe_float(_first_value(stats, ("ab", "AB")))
            if ab is not None and ab > 0:
                avg_val = hits / ab
        ab_sample = _safe_float(_first_value(stats, ("ab", "AB")))
        if avg_val is None or ab_sample is None or ab_sample <= 0:
            continue
        if leader is None or avg_val > leader[1]:
            leader = (player, avg_val)
    return leader


def _find_stat_leader(
    candidates: Sequence[tuple[Any, Mapping[str, Any]]],
    keys: Sequence[str],
) -> Optional[tuple[Any, float]]:
    leader: Optional[tuple[Any, float]] = None
    for player, stats in candidates:
        value = _safe_float(_first_value(stats, keys))
        if value is None:
            continue
        if leader is None or value > leader[1]:
            leader = (player, value)
    return leader


def _player_identifier(player: Any) -> Optional[str]:
    """Best-effort player identifier extraction for leader links."""

    for attr in ("player_id", "playerId", "id", "mlb_id"):  # noqa: SIM118
        candidate = getattr(player, attr, None)
        if candidate:
            return str(candidate)
    return None


def _calibration_summary(base_dir: Path) -> Dict[str, Any]:
    """Expose pitch calibration status for quick diagnostics."""

    defaults = {
        "enabled": False,
        "target_p_per_pa": None,
        "tolerance": None,
        "per_plate_cap": None,
        "per_game_cap": None,
        "min_pa": None,
        "ema_alpha": None,
    }
    if _load_playbalance_config is None:
        return defaults

    try:
        cfg = _load_playbalance_config(
            pbini_path=base_dir / "playbalance" / "PBINI.txt",
            overrides_path=base_dir / "data" / "playbalance_overrides.json",
        )
        pb = cfg.sections.get("PlayBalance")
        if pb is None:
            return defaults
        enabled = bool(getattr(pb, "pitchCalibrationEnabled", 0))
        return {
            "enabled": enabled,
            "target_p_per_pa": float(getattr(pb, "pitchCalibrationTarget", 0.0)),
            "tolerance": float(getattr(pb, "pitchCalibrationTolerance", 0.0)),
            "per_plate_cap": int(getattr(pb, "pitchCalibrationPerPlateCap", 0) or 0),
            "per_game_cap": int(getattr(pb, "pitchCalibrationPerGameCap", 0) or 0),
            "min_pa": int(getattr(pb, "pitchCalibrationMinPA", 0) or 0),
            "ema_alpha": float(getattr(pb, "pitchCalibrationEmaAlpha", 0.0)),
        }
    except Exception:
        return defaults


def _format_leader_entry(
    leader: Optional[tuple[Any, float]],
    *,
    stat: str,
) -> tuple[str, Optional[Dict[str, Any]]]:
    if leader is None:
        return "--", None
    player, value = leader
    name = _format_player_name(player)
    if name == "--":
        return "--", None
    if stat == "avg":
        if not math.isfinite(value):
            return "--", None
        formatted = f"{value:.3f}"
        if value < 1:
            formatted = formatted.lstrip("0")
        return f"{name} {formatted}".strip(), {
            "player_id": _player_identifier(player),
            "name": name,
            "stat": "avg",
            "value": round(value, 3),
        }
    if not math.isfinite(value):
        return "--", None
    count = int(round(value))
    return f"{name} {count}".strip(), {
        "player_id": _player_identifier(player),
        "name": name,
        "stat": stat,
        "value": count,
    }


def _is_pitcher_type(player: Any) -> bool:
    if player is None:
        return False
    if bool(getattr(player, "is_pitcher", False)):
        return True
    primary = str(getattr(player, "primary_position", "")).upper()
    return primary in {"P", "SP", "RP", "CL"}


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        result = float(value)
        if not math.isfinite(result):
            return None
        return result
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped in {"--", "NA", "N/A"}:
            return None
        try:
            result = float(stripped)
        except ValueError:
            return None
        if not math.isfinite(result):
            return None
        return result
    return None


def _first_value(stats: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in stats:
            return stats[key]
    return None


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

