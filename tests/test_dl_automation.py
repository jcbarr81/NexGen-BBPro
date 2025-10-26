from datetime import date, timedelta

from models.player import Player
from services.dl_automation import process_disabled_lists
from utils.player_loader import load_players_from_csv
from utils.player_writer import save_players_to_csv
from utils.roster_loader import load_roster


def _make_player(pid: str, *, injury_list: str, start: date, minimum: int = 15) -> Player:
    player = Player(
        player_id=pid,
        first_name="Test",
        last_name=pid,
        birthdate="1990-01-01",
        height=72,
        weight=190,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=0,
    )
    player.injured = True
    player.injury_list = injury_list
    player.injury_start_date = start.isoformat()
    player.injury_minimum_days = minimum
    player.injury_eligible_date = (start + timedelta(days=minimum)).isoformat()
    player.ready = False
    player.injury_description = "Test injury"
    return player


def _prepare_env(tmp_path, monkeypatch):
    base = tmp_path
    data = base / "data"
    rosters = data / "rosters"
    rosters.mkdir(parents=True)
    teams_path = data / "teams.csv"
    teams_path.write_text(
        "team_id,name,city,abbreviation,division,stadium,primary_color,secondary_color,owner_id\n"
        "TST,Testers,Test City,TST,East,Test Dome,#000000,#FFFFFF,owner\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("utils.path_utils.get_base_dir", lambda: base)
    monkeypatch.setattr("utils.roster_loader.get_base_dir", lambda: base)
    monkeypatch.setattr("utils.player_loader.get_base_dir", lambda: base)
    monkeypatch.setattr("utils.team_loader.get_base_dir", lambda: base)
    monkeypatch.setattr("services.dl_automation.get_base_dir", lambda: base)
    monkeypatch.setattr("utils.team_loader.load_stats", lambda: {"players": {}, "teams": {}})
    load_roster.cache_clear()
    load_players_from_csv.cache_clear()
    return data


def test_process_disabled_lists_activates_players(tmp_path, monkeypatch):
    data = _prepare_env(tmp_path, monkeypatch)
    player = _make_player("PINJ", injury_list="dl15", start=date(2025, 4, 1))
    save_players_to_csv([player], str(data / "players.csv"))
    roster_path = data / "rosters" / "TST.csv"
    roster_path.write_text(
        "PACT1,ACT\n"
        "PAAA1,AAA\n"
        "PLOW1,LOW\n"
        "PINJ,DL15\n",
        encoding="utf-8",
    )

    summary = process_disabled_lists(today="2025-04-25", auto_activate=True)

    assert summary.activated
    roster = load_roster("TST")
    assert "PINJ" in roster.act
    assert "PINJ" not in roster.dl
    players = load_players_from_csv("data/players.csv")
    activated = next(p for p in players if p.player_id == "PINJ")
    assert activated.injured is False
    assert activated.ready is True


def test_process_disabled_lists_tracks_rehab(tmp_path, monkeypatch):
    data = _prepare_env(tmp_path, monkeypatch)
    start = date(2025, 4, 1)
    player = _make_player("PREH", injury_list="dl45", start=start, minimum=10)
    player.injury_rehab_assignment = "aaa"
    player.injury_rehab_days = 3
    save_players_to_csv([player], str(data / "players.csv"))
    roster_path = data / "rosters" / "TST.csv"
    roster_path.write_text(
        "PACT1,ACT\n"
        "PAAA1,AAA\n"
        "PREH,DL45\n",
        encoding="utf-8",
    )

    summary = process_disabled_lists(
        today="2025-04-20",
        days_elapsed=2,
        auto_activate=False,
    )

    assert summary.rehab_ready or summary.alerts
    roster = load_roster("TST")
    assert "PREH" in roster.dl  # still awaiting manual activation
    players = load_players_from_csv("data/players.csv")
    rehab_player = next(p for p in players if p.player_id == "PREH")
    assert rehab_player.injury_rehab_days >= 5
    assert rehab_player.ready is True
