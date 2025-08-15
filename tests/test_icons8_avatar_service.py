import os
import sys
import types
import urllib.request

import pytest

# Provide a minimal PIL stub if Pillow is unavailable
if "PIL" not in sys.modules:
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("Image")
    pil_module.Image = image_module
    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = image_module

from services import icons8_avatar_service


def test_icons8_request_includes_user_agent(monkeypatch, tmp_path):
    monkeypatch.setenv("ICONS8_API_KEY", "dummy")

    expected_base = os.path.join(os.path.dirname(icons8_avatar_service.__file__), "..")
    orig_abspath = os.path.abspath

    def fake_abspath(path):
        if path == expected_base:
            return str(tmp_path)
        return orig_abspath(path)

    monkeypatch.setattr(icons8_avatar_service.os.path, "abspath", fake_abspath)

    def fake_urlopen(request, timeout=10, context=None):
        assert isinstance(request, urllib.request.Request)
        assert request.headers["User-agent"] == "Mozilla/5.0"
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError):
        icons8_avatar_service.fetch_icons8_avatar(
            "Test Player", "white", "#123456", "#654321"
        )
