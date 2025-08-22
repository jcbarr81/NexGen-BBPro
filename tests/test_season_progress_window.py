import sys, types

# ---- Stub PyQt6 modules ----
class DummySignal:
    def __init__(self):
        self._slot = None

    def connect(self, slot):
        self._slot = slot

    def emit(self):
        if self._slot:
            self._slot()


class Dummy:
    def __init__(self, *args, **kwargs):
        self.clicked = DummySignal()

    def __getattr__(self, name):
        return Dummy()

    def setVisible(self, *a, **k):
        pass

    def setWordWrap(self, *a, **k):
        pass

    def setText(self, *a, **k):
        pass

    def text(self):
        return ""

    def addWidget(self, *a, **k):
        pass

    def connect(self, *a, **k):
        pass

    def setWindowTitle(self, *a, **k):
        pass


class QLabel(Dummy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text = ""

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text


class QPushButton(Dummy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QDialog(Dummy):
    pass


class QVBoxLayout(Dummy):
    pass


qtwidgets = types.ModuleType("PyQt6.QtWidgets")
qtwidgets.QDialog = QDialog
qtwidgets.QLabel = QLabel
qtwidgets.QPushButton = QPushButton
qtwidgets.QVBoxLayout = QVBoxLayout
sys.modules["PyQt6"] = types.ModuleType("PyQt6")
sys.modules["PyQt6.QtWidgets"] = qtwidgets

# ---- Import window after stubs ----
from logic.season_manager import SeasonPhase
import ui.season_progress_window as spw


class DummyManager:
    def __init__(self):
        self.phase = SeasonPhase.REGULAR_SEASON

    def handle_phase(self):
        return "Regular Season"

    def advance_phase(self):
        pass


spw.SeasonManager = DummyManager


def test_simulate_day_until_midseason():
    schedule = [
        {"date": "2024-04-01", "home": "A", "away": "B"},
        {"date": "2024-04-02", "home": "A", "away": "B"},
        {"date": "2024-04-03", "home": "A", "away": "B"},
        {"date": "2024-04-04", "home": "A", "away": "B"},
    ]

    games = []

    def fake_sim(home, away):
        games.append((home, away))

    win = spw.SeasonProgressWindow(schedule=schedule, simulate_game=fake_sim)
    assert win.remaining_label.text() == "Days until Midseason: 2"

    win.simulate_day_button.clicked.emit()
    assert games == [("A", "B")]
    assert win.remaining_label.text() == "Days until Midseason: 1"

    win.simulate_day_button.clicked.emit()
    assert games == [("A", "B"), ("A", "B")]
    assert win.remaining_label.text() == "Days until Midseason: 0"

    # After the break the season continues
    win.simulate_day_button.clicked.emit()
    assert games == [("A", "B"), ("A", "B"), ("A", "B")]

    win.simulate_day_button.clicked.emit()
    assert games == [("A", "B"), ("A", "B"), ("A", "B"), ("A", "B")]

    # Further clicks should not simulate more games
    win.simulate_day_button.clicked.emit()
    assert games == [("A", "B"), ("A", "B"), ("A", "B"), ("A", "B")]
