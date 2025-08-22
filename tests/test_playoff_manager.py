from logic.playoff_manager import PlayoffManager


def test_playoff_flow(tmp_path):
    standings = {
        "A": {"wins": 10, "losses": 5},
        "B": {"wins": 9, "losses": 6},
        "C": {"wins": 12, "losses": 3},
        "D": {"wins": 7, "losses": 8},
        "E": {"wins": 6, "losses": 9},
    }
    path = tmp_path / "bracket.json"

    manager = PlayoffManager(standings, path=path)

    qualifiers = manager.determine_qualifiers()
    assert qualifiers == ["C", "A", "B", "D"]

    bracket = manager.create_bracket(qualifiers)
    assert bracket["rounds"][0] == [
        {"home": "C", "away": "D"},
        {"home": "A", "away": "B"},
    ]
    assert bracket["rounds"][1] == [
        {"home": "winner_0", "away": "winner_1"}
    ]

    manager.save_bracket(bracket)
    assert path.exists()
    loaded = manager.load_bracket()
    assert loaded == bracket

