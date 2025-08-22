import csv

from utils.roster_loader import load_roster


def test_load_roster_promotes_replacements(tmp_path):
    roster_file = tmp_path / "T.csv"
    rows = [
        ["p1", "ACT"],
        ["p2", "AAA"],
        ["p3", "DL"],
        ["p4", "IR"],
        ["p5", "LOW"],
    ]
    with roster_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    roster = load_roster("T", roster_dir=tmp_path)

    assert roster.dl == ["p3"]
    assert roster.ir == ["p4"]
    assert "p2" in roster.act
    assert "p5" in roster.act
    assert roster.aaa == []
    assert roster.low == []
