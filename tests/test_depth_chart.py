from models.roster import Roster


def _setup_base(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.path_utils.get_base_dir", lambda: tmp_path)
    (tmp_path / "data" / "depth_charts").mkdir(parents=True, exist_ok=True)


def test_depth_chart_roundtrip(tmp_path, monkeypatch):
    _setup_base(tmp_path, monkeypatch)
    from utils import depth_chart

    chart = depth_chart.load_depth_chart("ABC")
    assert chart["C"] == []
    chart["C"] = ["p1", "p2"]
    depth_chart.save_depth_chart("ABC", chart)

    loaded = depth_chart.load_depth_chart("ABC")
    assert loaded["C"] == ["p1", "p2"]
    # Unknown positions should be dropped
    path = tmp_path / "data" / "depth_charts" / "ABC.json"
    data = path.read_text(encoding="utf-8")
    assert "p1" in data


def test_promote_depth_chart_replacement(tmp_path, monkeypatch):
    _setup_base(tmp_path, monkeypatch)
    from utils.depth_chart import default_depth_chart, save_depth_chart
    from services.depth_chart_manager import promote_depth_chart_replacement

    chart = default_depth_chart()
    chart["C"] = ["AAA1"]
    save_depth_chart("TEAM", chart)
    roster = Roster(team_id="TEAM", act=["ACT1"], aaa=["AAA1"], low=[], dl=[], ir=[], dl_tiers={})

    promoted = promote_depth_chart_replacement(roster, "C")
    assert promoted is True
    assert "AAA1" in roster.act
    assert "AAA1" not in roster.aaa


def test_promote_depth_chart_respects_exclusions(tmp_path, monkeypatch):
    _setup_base(tmp_path, monkeypatch)
    from utils.depth_chart import default_depth_chart, save_depth_chart
    from services.depth_chart_manager import promote_depth_chart_replacement

    chart = default_depth_chart()
    chart["SS"] = ["AAA2"]
    save_depth_chart("TEAM", chart)
    roster = Roster(team_id="TEAM", act=["SS1"], aaa=["AAA2"], low=[], dl=[], ir=[], dl_tiers={})

    assert promote_depth_chart_replacement(roster, "SS", exclude={"AAA2"}) is False
    assert "AAA2" in roster.aaa
