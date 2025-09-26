from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA_DIR = ROOT / "data"
PLAYERS_FILE = DATA_DIR / "players.csv"
STATS_FILE = DATA_DIR / "season_stats.json"


def _load_lookup():
    try:
        stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        stats = {"players": {}, "teams": {}}
    player_stats = stats.get("players", {})
    lookup: dict[str, SimpleNamespace] = {}
    with PLAYERS_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("player_id") or ""
            if not pid:
                continue
            is_pitcher = (row.get("is_pitcher", "").strip().lower() in {"1", "true", "yes"})
            lookup[pid] = SimpleNamespace(
                player_id=pid,
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""),
                is_pitcher=is_pitcher,
                season_stats=player_stats.get(pid, {}),
            )
    return lookup, stats.get("teams", {})


def main(team_id: str = "MIN") -> None:
    from utils.roster_loader import load_roster

    players, team_stats = _load_lookup()
    roster = load_roster(team_id)
    batter_ids = [pid for pid in roster.act if (pid in players and not getattr(players[pid], "is_pitcher", False))]
    print(f"Team {team_id} active batters: {len(batter_ids)}  |  STATS_FILE={STATS_FILE.resolve()}")

    def _has(b):
        s = getattr(b, "season_stats", {}) or {}
        return any(s.get(k, 0) for k in ("ab", "pa", "h", "bb", "hr"))

    hitters = [players[pid] for pid in batter_ids]
    with_stats = [b for b in hitters if _has(b)]
    without = [b for b in hitters if not _has(b)]
    print(f"Batters with stats: {len(with_stats)}; without: {len(without)}")
    if with_stats:
        print("Examples with stats:")
        for b in with_stats[:5]:
            s = b.season_stats
            print(f"  {b.player_id} {b.first_name} {b.last_name} | G={s.get('g')} AB={s.get('ab')} H={s.get('h')} BB={s.get('bb')} HR={s.get('hr')} AVG={s.get('avg')}")
    if without:
        print("Examples without stats:")
        for b in without[:5]:
            print(f"  {b.player_id} {b.first_name} {b.last_name}")

    # Compute and show team batting summary from players (as UI does)
    ab=h=bb=hbp=sf=hr=r=sb=b2=b3=0
    for b in hitters:
        s = b.season_stats or {}
        ab += s.get("ab", 0) or 0
        h += s.get("h", 0) or 0
        bb += s.get("bb", 0) or 0
        hbp += s.get("hbp", 0) or 0
        sf += s.get("sf", 0) or 0
        hr += s.get("hr", 0) or 0
        r += s.get("r", 0) or 0
        sb += s.get("sb", 0) or 0
        b2 += s.get("b2", s.get("2b", 0)) or 0
        b3 += s.get("b3", s.get("3b", 0)) or 0
    singles = h - b2 - b3 - hr
    tb = singles + 2*b2 + 3*b3 + 4*hr
    avg = h/ab if ab else 0.0
    obp = (h + bb + hbp) / (ab + bb + hbp + sf) if (ab + bb + hbp + sf) else 0.0
    slg = tb/ab if ab else 0.0
    print(f"Summary AVG={avg:.3f} OBP={obp:.3f} SLG={slg:.3f} R={r} HR={hr} SB={sb}")
    team = team_stats.get(team_id, {})
    print(f"Team totals (season_stats.json): R={team.get('r')} OppPA={team.get('opp_pa')}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "MIN")
