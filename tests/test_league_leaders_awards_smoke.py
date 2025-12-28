from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
import shutil

from tests.qt_stubs import patch_qt

patch_qt()


def _pick_player_ids(players_path: Path) -> tuple[str, str]:
    hitter_id = ""
    pitcher_id = ""
    with players_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            is_pitcher = (row.get("is_pitcher") or "").strip().lower() in {
                "1",
                "true",
                "yes",
            }
            player_id = (row.get("player_id") or "").strip()
            if not player_id:
                continue
            if is_pitcher and not pitcher_id:
                pitcher_id = player_id
            if not is_pitcher and not hitter_id:
                hitter_id = player_id
            if hitter_id and pitcher_id:
                break
    if not hitter_id or not pitcher_id:
        raise AssertionError("Unable to locate hitter and pitcher IDs for test data.")
    return hitter_id, pitcher_id


def test_league_leaders_and_awards_smoke(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", tmp_path, raising=False)
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    repo_players = Path(__file__).resolve().parents[1] / "data" / "players.csv"
    if not repo_players.exists():
        raise AssertionError("Repo players.csv missing; smoke test cannot run.")
    shutil.copy(repo_players, data_dir / "players.csv")

    hitter_id, pitcher_id = _pick_player_ids(data_dir / "players.csv")
    season_stats = {
        "players": {
            hitter_id: {
                "pa": 40,
                "ab": 38,
                "h": 15,
                "avg": 15 / 38,
                "hr": 5,
                "rbi": 12,
                "ops": 0.900,
            },
            pitcher_id: {
                "ip": 12.0,
                "outs": 36,
                "era": 2.25,
                "whip": 0.90,
                "so": 15,
                "sv": 3,
            },
        },
        "teams": {"T1": {"g": 10}, "T2": {"g": 10}},
        "history": [],
    }
    (data_dir / "season_stats.json").write_text(
        json.dumps(season_stats, indent=2), encoding="utf-8"
    )

    import importlib
    import ui.league_leaders_window as llw
    from playbalance.awards_manager import AwardsManager

    importlib.reload(llw)
    llw.load_players_from_csv.cache_clear(llw.PLAYERS_FILE)

    window = llw.LeagueLeadersWindow.__new__(llw.LeagueLeadersWindow)
    window._min_pa = int(round(10 * 3.1))
    window._min_ip = int(round(10 * 1.0))

    players = {p.player_id: p for p in window._load_players_with_stats()}
    hitters = [p for p in players.values() if not getattr(p, "is_pitcher", False)]
    pitchers = [p for p in players.values() if getattr(p, "is_pitcher", False)]
    qualified_hitters = window._qualified_batters(hitters)
    qualified_pitchers = window._qualified_pitchers(pitchers)

    hr_leaders = window._leaders_for_category(
        qualified_hitters,
        hitters,
        "hr",
        pitcher_only=False,
        descending=True,
        limit=5,
    )
    sv_leaders = window._leaders_for_category(
        qualified_pitchers,
        pitchers,
        "sv",
        pitcher_only=True,
        descending=True,
        limit=5,
    )

    assert hr_leaders and hr_leaders[0][0].player_id == hitter_id
    assert sv_leaders and sv_leaders[0][0].player_id == pitcher_id

    awards = AwardsManager(
        players,
        {hitter_id: season_stats["players"][hitter_id]},
        {pitcher_id: season_stats["players"][pitcher_id]},
        min_pa=0,
        min_ip=0.0,
    ).select_award_winners()

    assert awards["MVP"].player.player_id == hitter_id
    assert awards["CY_YOUNG"].player.player_id == pitcher_id
