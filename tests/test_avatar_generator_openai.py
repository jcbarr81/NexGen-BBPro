import base64
from io import BytesIO
from types import SimpleNamespace

import pytest
pytest.importorskip("PIL")
from PIL import Image

from utils import avatar_generator


def _fake_b64_png(size: int) -> str:
    img = Image.new("RGBA", (size, size))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_generates_avatar_at_requested_size(tmp_path, monkeypatch):
    size = 64
    monkeypatch.setattr(
        avatar_generator,
        "_TEAM_COLOR_MAP",
        {"TST": {"primary": "#112233", "secondary": "#445566"}},
    )

    calls = {}

    class DummyImages:
        def generate(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(data=[SimpleNamespace(b64_json=_fake_b64_png(size))])

    monkeypatch.setattr(avatar_generator, "client", SimpleNamespace(images=DummyImages()))

    out_file = tmp_path / "avatar.png"
    avatar_generator.generate_avatar("Test Player", "TST", str(out_file), size=size)

    assert calls["size"] == f"{size}x{size}"
    assert "Test Player" in calls["prompt"]
    assert out_file.exists()
    with Image.open(out_file) as img:
        assert img.size == (size, size)
