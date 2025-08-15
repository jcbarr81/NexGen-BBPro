import importlib
import os
import sys
import types
import urllib.request
import urllib.parse

import pytest


def test_icons8_request_includes_headers(monkeypatch, tmp_path):
    monkeypatch.setenv("ICONS8_API_KEY", "dummy")

    # Stub minimal PIL modules so icons8_avatar_service can import without Pillow
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("Image")
    pil_module.Image = image_module
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", image_module)

    from services import icons8_avatar_service as svc
    importlib.reload(svc)

    expected_base = os.path.join(os.path.dirname(svc.__file__), "..")
    orig_abspath = os.path.abspath

    def fake_abspath(path):
        if path == expected_base:
            return str(tmp_path)
        return orig_abspath(path)

    monkeypatch.setattr(svc.os.path, "abspath", fake_abspath)

    def fake_urlopen(request, timeout=10, context=None):
        assert isinstance(request, urllib.request.Request)
        assert request.headers["User-agent"] == "Mozilla/5.0"
        assert request.get_header("X-api-key") == "dummy"
        assert request.headers["Referer"] == "https://app.icons8.com"
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError):
        svc.fetch_icons8_avatar(
            "Test Player", "white", "#123456", "#654321"
        )
