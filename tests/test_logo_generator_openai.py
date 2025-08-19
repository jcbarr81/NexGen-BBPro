import base64
from io import BytesIO
from types import SimpleNamespace

import pytest
pytest.importorskip("PIL")
from PIL import Image

from utils import logo_generator
from models.team import Team


def _fake_b64_png(size: int) -> str:
    img = Image.new("RGBA", (size, size))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_generates_logo_and_calls_callback(tmp_path, monkeypatch):
    team = Team(
        team_id="TST",
        name="Testers",
        city="Testville",
        abbreviation="TST",
        division="Test",
        stadium="Test Field",
        primary_color="#112233",
        secondary_color="#445566",
        owner_id="0",
    )

    # Patch load_teams to return our single team
    monkeypatch.setattr(logo_generator, "load_teams", lambda _: [team])

    calls = {}
    logo_size = 256

    class DummyImages:
        def generate(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(data=[SimpleNamespace(b64_json=_fake_b64_png(logo_size))])

    monkeypatch.setattr(logo_generator, "client", SimpleNamespace(images=DummyImages()))

    progress = []

    def cb(done, total):
        progress.append((done, total))

    out_dir = tmp_path
    logo_generator.generate_team_logos(out_dir=str(out_dir), size=logo_size, progress_callback=cb)

    assert calls["size"] == f"{logo_size}x{logo_size}"
    assert "Testville" in calls["prompt"]
    assert "Testers" in calls["prompt"]
    assert "#112233" in calls["prompt"]
    assert "#445566" in calls["prompt"]

    outfile = out_dir / "tst.png"
    assert outfile.exists()
    with Image.open(outfile) as img:
        assert img.size == (logo_size, logo_size)
    assert progress == [(1, 1)]


def test_auto_logo_fallback_without_client(tmp_path, monkeypatch):
    monkeypatch.setattr(logo_generator, "client", None)
    monkeypatch.setattr(logo_generator, "load_teams", lambda _: [])

    called = {}

    def fake_fallback(teams, out_dir, size, progress_callback):
        called["args"] = (teams, out_dir, size, progress_callback)

    monkeypatch.setattr(logo_generator, "_auto_logo_fallback", fake_fallback)

    logo_generator.generate_team_logos(out_dir=str(tmp_path))
    assert "args" in called


def test_raises_without_client_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(logo_generator, "client", None)
    monkeypatch.setattr(logo_generator, "load_teams", lambda _: [])
    with pytest.raises(RuntimeError):
        logo_generator.generate_team_logos(out_dir=str(tmp_path), allow_auto_logo=False)
