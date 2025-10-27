from playbalance.training_camp import run_training_camp
from models.player import Player


def make_player(pid: str) -> Player:
    return Player(
        player_id=pid,
        first_name="Test",
        last_name="Player",
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=0,
        ch=40,
        ph=30,
        pot_ch=70,
        pot_ph=65,
    )


def test_training_camp_returns_reports_and_sets_ready(monkeypatch) -> None:
    calls = {}

    def _capture_reports(reports, **kwargs):
        calls["count"] = len(list(reports))

    monkeypatch.setattr("playbalance.training_camp.record_training_session", _capture_reports)

    players = [make_player("p1"), make_player("p2")]
    assert all(not p.ready for p in players)

    reports = run_training_camp(players)
    assert len(reports) == len(players)
    assert all(p.ready for p in players)
    assert any(report.changes for report in reports)
    assert calls.get("count") == len(players)
