import pathlib

from playbalance.player_loader import load_lineup, load_pitching_staff


def test_load_lineup_missing_file(tmp_path):
    players = {}
    missing_path = tmp_path / "missing_lineup.csv"
    assert load_lineup(missing_path, players) == []


def test_load_pitching_staff_missing_file(tmp_path):
    players = {}
    missing_path = tmp_path / "missing_roster.csv"
    assert load_pitching_staff(missing_path, players) == []
