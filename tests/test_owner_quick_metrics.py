from __future__ import annotations

import json
from types import SimpleNamespace

from ui.analytics.quick_metrics import gather_owner_quick_metrics


def test_gather_owner_quick_metrics_handles_missing(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "standings.json").write_text(json.dumps({}), encoding="utf-8")
    (data_dir / "schedule.csv").write_text(
        "date,home,away,result,played\n", encoding="utf-8"
    )

    roster = SimpleNamespace(dl=[], ir=[], act=[])
    players: dict[str, object] = {}

    metrics = gather_owner_quick_metrics(
        "TST", base_path=tmp_path, roster=roster, players=players
    )

    assert metrics["record"] == "--"
    assert metrics["calibration"]["enabled"] is False
    assert metrics["bullpen"]["total"] == 0
    assert metrics["matchup"]["opponent"] == "--"
    assert metrics["batting_leaders"] == {
        "avg": "--",
        "hr": "--",
        "rbi": "--",
    }
    assert metrics["pitching_leaders"] == {
        "wins": "--",
        "so": "--",
        "saves": "--",
    }
    meta = metrics.get("leader_meta", {})
    assert meta.get("batting") == {}
    assert meta.get("pitching") == {}


def test_gather_owner_quick_metrics_team_leader_rows(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "standings.json").write_text(json.dumps({}), encoding="utf-8")
    (data_dir / "schedule.csv").write_text(
        "date,home,away,result,played\n", encoding="utf-8"
    )
    season_stats = {
        "players": {
            "BAT1": {"ab": 100, "h": 30, "avg": 0.300, "hr": 12, "rbi": 40},
            "BAT2": {"ab": 80, "h": 35, "avg": 0.438, "hr": 10, "rbi": 30},
            "PIT1": {"ip": 95.0, "w": 12, "so": 150, "sv": 0},
            "PIT2": {"ip": 60.0, "w": 2, "so": 65, "sv": 22},
        },
        "teams": {},
        "history": [],
    }
    (data_dir / "season_stats.json").write_text(
        json.dumps(season_stats), encoding="utf-8"
    )

    roster = SimpleNamespace(
        dl=[],
        ir=[],
        act=["BAT1", "BAT2", "PIT1", "PIT2"],
    )
    players = {
        "BAT1": SimpleNamespace(
            player_id="BAT1",
            first_name="Slugger",
            last_name="One",
            is_pitcher=False,
            primary_position="RF",
        ),
        "BAT2": SimpleNamespace(
            player_id="BAT2",
            first_name="Slugger",
            last_name="Two",
            is_pitcher=False,
            primary_position="CF",
        ),
        "PIT1": SimpleNamespace(
            player_id="PIT1",
            first_name="Ace",
            last_name="Starter",
            is_pitcher=True,
            primary_position="SP",
        ),
        "PIT2": SimpleNamespace(
            player_id="PIT2",
            first_name="Closer",
            last_name="Guy",
            is_pitcher=True,
            primary_position="RP",
        ),
    }

    metrics = gather_owner_quick_metrics(
        "TST", base_path=tmp_path, roster=roster, players=players
    )

    assert metrics["batting_leaders"]["avg"] == "Slugger Two .438"
    assert metrics["batting_leaders"]["hr"] == "Slugger One 12"
    assert metrics["batting_leaders"]["rbi"] == "Slugger One 40"
    assert metrics["pitching_leaders"]["wins"] == "Ace Starter 12"
    assert metrics["pitching_leaders"]["so"] == "Ace Starter 150"
    assert metrics["pitching_leaders"]["saves"] == "Closer Guy 22"
    leader_meta = metrics["leader_meta"]
    assert leader_meta["batting"]["avg"]["player_id"] == "BAT2"
    assert leader_meta["batting"]["hr"]["player_id"] == "BAT1"
    assert leader_meta["batting"]["rbi"]["player_id"] == "BAT1"
    assert leader_meta["pitching"]["wins"]["player_id"] == "PIT1"
    assert leader_meta["pitching"]["so"]["player_id"] == "PIT1"
    assert leader_meta["pitching"]["saves"]["player_id"] == "PIT2"
