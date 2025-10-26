import csv

from utils.roster_loader import load_roster


def test_load_roster_promotes_replacements(tmp_path):
    roster_file = tmp_path / "T.csv"
    rows = [
        ["p1", "ACT"],
        ["p2", "AAA"],
        ["p3", "DL15"],
        ["p4", "DL45"],
        ["p5", "IR"],
        ["p6", "LOW"],
    ]
    with roster_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    roster = load_roster("T", roster_dir=tmp_path)

    assert roster.dl == ["p3", "p4"]
    assert roster.dl_tiers["p3"] == "dl15"
    assert roster.dl_tiers["p4"] == "dl45"
    assert roster.ir == ["p5"]
    assert "p2" in roster.act
    assert "p6" in roster.act
    assert roster.aaa == []
    assert roster.low == []
