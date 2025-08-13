import pytest
from utils.team_loader import load_teams, save_team_settings


def _create_team_file(tmp_path):
    file = tmp_path / "teams.csv"
    file.write_text(
        "team_id,name,city,abbreviation,division,stadium,primary_color,secondary_color,owner_id\n"
        "1,Team,City,TC,DIV,Stadium,#FFFFFF,#000000,owner\n"
    )
    return file


def test_sanitize_hex_colors(tmp_path):
    team_file = _create_team_file(tmp_path)
    team = load_teams(str(team_file))[0]
    team.primary_color = "123abc"  # missing '#', lowercase
    save_team_settings(team, str(team_file))

    updated = load_teams(str(team_file))[0]
    assert updated.primary_color == "#123ABC"


def test_invalid_hex_color_raises(tmp_path):
    team_file = _create_team_file(tmp_path)
    team = load_teams(str(team_file))[0]
    team.secondary_color = "ZZZZZZ"  # invalid characters
    with pytest.raises(ValueError):
        save_team_settings(team, str(team_file))
