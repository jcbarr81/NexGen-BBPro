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


def test_round_trip_preserves_appearance(tmp_path):
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
        endurance=40,
        control=50,
        movement=60,
        hold_runner=55,
        fb=70,
        cu=60,
        cb=50,
        sl=40,
        si=45,
        scb=35,
        kn=20,
        fa=65,
        ethnicity="Anglo",
        skin_tone="medium",
        hair_color="black",
        facial_hair="mustache",
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
        ch=50,
        ph=55,
        sp=60,
        pl=65,
        vl=40,
        sc=45,
        fa=50,
        ethnicity="Anglo",
        skin_tone="light",
        hair_color="brown",
        facial_hair="beard",
    )
    save_players_to_csv([pitcher, hitter], file_path)
    loaded = load_players_from_csv(file_path)
    loaded_dict = {p.player_id: p for p in loaded}
    for original in [pitcher, hitter]:
        loaded_player = loaded_dict[original.player_id]
        assert loaded_player.ethnicity == original.ethnicity
        assert loaded_player.skin_tone == original.skin_tone
        assert loaded_player.hair_color == original.hair_color
        assert loaded_player.facial_hair == original.facial_hair


def test_round_trip_preserves_archetypes(tmp_path):
    file_path = tmp_path / "players.csv"
    pitcher = Pitcher(
        player_id="p2",
        first_name="Ace",
        last_name="Arm",
        birthdate="1992-03-03",
        height=74,
        weight=200,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=12,
        arm=70,
        endurance=60,
        control=65,
        movement=62,
        hold_runner=50,
        fb=80,
        cu=65,
        cb=55,
        sl=70,
        si=60,
        scb=50,
        kn=0,
        role="SP",
        pitcher_archetype="power_sp",
    )
    hitter = Player(
        player_id="h2",
        first_name="Slug",
        last_name="Ger",
        birthdate="1994-04-04",
        height=72,
        weight=210,
        bats="L",
        primary_position="RF",
        other_positions=[],
        gf=18,
        arm=65,
        ch=55,
        ph=80,
        sp=45,
        pl=70,
        vl=50,
        sc=55,
        fa=50,
        hitter_archetype="power",
    )
    save_players_to_csv([pitcher, hitter], file_path)
    loaded = load_players_from_csv(file_path)
    loaded_dict = {p.player_id: p for p in loaded}
    assert loaded_dict["p2"].pitcher_archetype == "power_sp"
    assert loaded_dict["h2"].hitter_archetype == "power"
