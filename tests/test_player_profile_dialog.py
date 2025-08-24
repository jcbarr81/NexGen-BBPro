import sys
import types
from types import SimpleNamespace
import importlib


class Dummy:
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return Dummy()

    def addWidget(self, *args, **kwargs):
        pass

    def addLayout(self, *args, **kwargs):
        pass

    def setLayout(self, *args, **kwargs):
        pass

    def setPixmap(self, *args, **kwargs):
        pass

    def scaled(self, *args, **kwargs):
        return self

    def isNull(self):
        return True

    def setWindowTitle(self, *args, **kwargs):
        pass

    def adjustSize(self, *args, **kwargs):
        pass

    def sizeHint(self, *args, **kwargs):
        return self

    def setFixedSize(self, *args, **kwargs):
        pass


qtwidgets = types.ModuleType("PyQt6.QtWidgets")
for name in [
    "QDialog",
    "QLabel",
    "QVBoxLayout",
    "QHBoxLayout",
    "QGridLayout",
    "QGroupBox",
]:
    setattr(qtwidgets, name, Dummy)

sys.modules.setdefault("PyQt6", types.ModuleType("PyQt6"))
sys.modules["PyQt6.QtWidgets"] = qtwidgets
sys.modules["PyQt6.QtGui"] = types.ModuleType("PyQt6.QtGui")
sys.modules["PyQt6.QtGui"].QPixmap = Dummy
sys.modules["PyQt6.QtCore"] = types.ModuleType("PyQt6.QtCore")
sys.modules["PyQt6.QtCore"].Qt = SimpleNamespace(
    AspectRatioMode=SimpleNamespace(KeepAspectRatio=None),
    TransformationMode=SimpleNamespace(SmoothTransformation=None),
)

import ui.player_profile_dialog as ppd
importlib.reload(ppd)


def test_player_profile_dialog_uses_history(monkeypatch):
    history = [
        {"players": {"p1": {"ratings": {"ch": 40}, "stats": {"g": 10}}}},
        {"players": {"p1": {"ratings": {"ch": 45}, "stats": {"g": 12}}}},
    ]
    monkeypatch.setattr(
        ppd,
        "load_stats",
        lambda: {"players": {}, "teams": {}, "history": history},
    )

    player = SimpleNamespace(
        player_id="p1",
        first_name="T",
        last_name="P",
        birthdate="2000-01-01",
        height=70,
        weight=180,
        bats="R",
        primary_position="C",
        other_positions=[],
        gf=50,
        ch=50,
        ph=60,
        sp=70,
        pl=80,
        vl=65,
        sc=55,
        fa=40,
        arm=85,
    )

    calls = []

    def fake_build_grid(self, title, data):
        calls.append(title)
        return Dummy()

    monkeypatch.setattr(ppd.PlayerProfileDialog, "_build_grid", fake_build_grid)

    ppd.PlayerProfileDialog(player)

    assert "Year 1 Ratings" in calls
    assert "Year 1 Stats" in calls
    assert "Year 2 Ratings" in calls
    assert "Year 2 Stats" in calls
