import csv
from models.player import Player
from models.pitcher import Pitcher
from utils.player_loader import load_players_from_csv
from utils.player_writer import save_players_to_csv


def test_save_players_to_csv_marks_pitchers(tmp_path):
    file_path = tmp_path / "players.csv"
    pitcher = Pitcher(
        player_id="p1",
        first_name="Pitch",
        last_name="Er",
        birthdate="1990-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=10,
        arm=50,
        role="SP",
    )
    hitter = Player(
        player_id="h1",
        first_name="Hit",
        last_name="Ter",
        birthdate="1991-02-02",
        height=70,
        weight=175,
        bats="L",
        primary_position="1B",
        other_positions=[],
        gf=20,
        arm=60,
    )
    save_players_to_csv([pitcher, hitter], file_path)
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    rows_by_id = {
        row["player_id"]: (row["is_pitcher"], row.get("role", "")) for row in rows
    }
    assert rows_by_id["p1"] == ("1", "SP")
    assert rows_by_id["h1"] == ("0", "")
    loaded_players = load_players_from_csv(file_path)
    roles = {p.player_id: getattr(p, "role", "") for p in loaded_players if isinstance(p, Pitcher)}
    assert roles["p1"] == "SP"
