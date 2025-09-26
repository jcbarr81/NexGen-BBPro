from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from utils.roster_loader import load_roster

DATA_DIR = ROOT / "data"
PLAYERS_FILE = DATA_DIR / "players.csv"
STATS_FILE = DATA_DIR / "season_stats.json"


def load_players_lookup():
    import csv

    try:
        stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        stats = {"players": {}, "teams": {}}
    player_stats = stats.get("players", {})
    lookup: dict[str, SimpleNamespace] = {}
    with PLAYERS_FILE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pid = row.get("player_id") or ""
            if not pid:
                continue
            is_pitcher = (row.get("is_pitcher", "").strip().lower() in {"1", "true", "yes"})
            stats_block = player_stats.get(pid, {})
            lookup[pid] = SimpleNamespace(
                player_id=pid,
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""),
                is_pitcher=is_pitcher,
                season_stats=stats_block,
            )
    return lookup


def main(team_id: str = "MIN") -> None:
    players = load_players_lookup()
    roster = load_roster(team_id)
    pitcher_ids = [pid for pid in roster.act if pid in players and getattr(players[pid], "is_pitcher", False)]
    print(f"Team {team_id} active pitchers: {len(pitcher_ids)}")
    for pid in pitcher_ids:
        p = players[pid]
        stats = dict(getattr(p, "season_stats", {}) or {})
        ip = stats.get("ip")
        outs = stats.get("outs")
        g = stats.get("g")
        # Emulate TeamStatsWindow logic
        PITCHING_COLS = ["w","l","era","g","gs","sv","ip","h","er","bb","so","whip"]
        def _coerce_float(value):
            if value is None: return None
            try:
                return float(value)
            except Exception:
                try:
                    return float(str(value).strip())
                except Exception:
                    return None
        def _has_stat_value(value):
            numeric = _coerce_float(value)
            if numeric is not None:
                return abs(numeric) > 1e-9
            if isinstance(value, str):
                return bool(value.strip())
            return bool(value)
        def _player_has_stats(stats: dict, columns: list[str]) -> bool:
            if not stats:
                return False
            if _has_stat_value(stats.get("g")):
                return True
            for key in columns:
                if key == "g":
                    continue
                if _has_stat_value(stats.get(key)):
                    return True
            return False
        has_stats = _player_has_stats(stats, PITCHING_COLS)
        print(f"{pid} {p.first_name} {p.last_name} | has_stats={has_stats} g={g} ip={ip} outs={outs} keys={sorted(stats.keys())[:8]}")


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else "MIN")
