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
        self._enabled = True

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

    def setEnabled(self, value):
        self._enabled = value

    def isEnabled(self):
        return self._enabled

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


class QMessageBox:
    last = None

    @staticmethod
    def warning(parent, title, message):
        QMessageBox.last = (title, message)


qtwidgets = types.ModuleType("PyQt6.QtWidgets")
qtwidgets.QDialog = QDialog
qtwidgets.QLabel = QLabel
qtwidgets.QPushButton = QPushButton
qtwidgets.QVBoxLayout = QVBoxLayout
qtwidgets.QMessageBox = QMessageBox
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
spw.QMessageBox = QMessageBox


def test_simulate_day_until_midseason(tmp_path, monkeypatch):
    schedule = [
        {"date": "2024-04-01", "home": "A", "away": "B"},
        {"date": "2024-04-02", "home": "A", "away": "B"},
        {"date": "2024-04-03", "home": "A", "away": "B"},
        {"date": "2024-04-04", "home": "A", "away": "B"},
    ]

    games = []

    def fake_sim(home, away):
        games.append((home, away))

    monkeypatch.setattr(spw, "PROGRESS_FILE", tmp_path / "progress.json")
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


def test_simulate_day_warns_when_missing_data(tmp_path, monkeypatch):
    schedule = [{"date": "2024-04-01", "home": "A", "away": "B"}]

    def bad_sim(home, away):  # pragma: no cover - simple stub
        raise FileNotFoundError("Team A lineup missing")

    QMessageBox.last = None
    monkeypatch.setattr(spw, "PROGRESS_FILE", tmp_path / "progress.json")
    win = spw.SeasonProgressWindow(schedule=schedule, simulate_game=bad_sim)
    win.simulate_day_button.clicked.emit()
    assert QMessageBox.last == (
        "Missing Lineup or Pitching", "Team A lineup missing"
    )


from datetime import date
from models.player import Player


def _player(age: int) -> Player:
    today = date.today()
    birthdate = date(today.year - age, today.month, today.day).isoformat()
    return Player(
        player_id=str(age),
        first_name="A",
        last_name="B",
        birthdate=birthdate,
        height=72,
        weight=180,
        bats="R",
        primary_position="1b",
        other_positions=[],
        gf=0,
        ch=50,
        ph=50,
        sp=50,
        fa=50,
        arm=50,
    )


def test_offseason_resets_to_preseason():
    class OffseasonManager:
        def __init__(self):
            self.phase = SeasonPhase.OFFSEASON
            self.players = {"old": _player(41), "young": _player(30)}

        def handle_phase(self):
            return "Offseason"

        def save(self):
            pass

        def advance_phase(self):
            self.phase = self.phase.next()

    spw.SeasonManager = OffseasonManager
    win = spw.SeasonProgressWindow()
    win._next_phase()
    assert win.manager.phase == SeasonPhase.PRESEASON
    assert "old" not in win.manager.players
    import logic.season_manager as sm
    assert sm.TRADE_DEADLINE.year == date.today().year + 1


def test_preseason_actions_require_sequence():
    class PreseasonManager:
        def __init__(self):
            self.phase = SeasonPhase.PRESEASON
            self.players = {}
            team_a = types.SimpleNamespace(
                abbreviation="A", act_roster=[], aaa_roster=[], low_roster=[]
            )
            team_b = types.SimpleNamespace(
                abbreviation="B", act_roster=[], aaa_roster=[], low_roster=[]
            )
            self.teams = [team_a, team_b]

        def handle_phase(self):
            return "Preseason"

        def save(self):
            pass

        def advance_phase(self):
            self.phase = self.phase.next()

    spw.SeasonManager = PreseasonManager
    win = spw.SeasonProgressWindow()

    assert not win.training_camp_button.isEnabled()
    assert not win.generate_schedule_button.isEnabled()
    assert not win.next_button.isEnabled()

    win.free_agency_button.clicked.emit()
    assert win.training_camp_button.isEnabled()
    assert "No unsigned players available" in win.notes_label.text()

    win.training_camp_button.clicked.emit()
    assert win.generate_schedule_button.isEnabled()
    assert "Training camp completed" in win.notes_label.text()

    win.generate_schedule_button.clicked.emit()
    assert len(win.simulator.schedule) == 162
    assert win.next_button.isEnabled()
    assert "Schedule generated with" in win.notes_label.text()


def test_generate_schedule_loads_teams_from_csv(monkeypatch, tmp_path):
    import csv

    class PreseasonManager:
        def __init__(self):
            self.phase = SeasonPhase.PRESEASON
            self.players = {}
            self.teams = []

        def handle_phase(self):
            return "Preseason"

        def save(self):
            pass

        def advance_phase(self):
            pass

    spw.SeasonManager = PreseasonManager
    teams_file = tmp_path / "teams.csv"
    with teams_file.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["abbreviation"])
        writer.writeheader()
        writer.writerow({"abbreviation": "A"})
        writer.writerow({"abbreviation": "B"})
    schedule_file = tmp_path / "schedule.csv"
    monkeypatch.setattr(spw, "TEAMS_FILE", teams_file)
    monkeypatch.setattr(spw, "SCHEDULE_FILE", schedule_file)

    win = spw.SeasonProgressWindow()
    win._generate_schedule()
    assert len(win.simulator.schedule) > 0
    assert schedule_file.exists()


def test_progress_persists_between_sessions(monkeypatch, tmp_path):
    class PreseasonManager:
        def __init__(self):
            self.phase = SeasonPhase.PRESEASON
            self.players = {}
            team_a = types.SimpleNamespace(
                abbreviation="A", act_roster=[], aaa_roster=[], low_roster=[]
            )
            team_b = types.SimpleNamespace(
                abbreviation="B", act_roster=[], aaa_roster=[], low_roster=[]
            )
            self.teams = [team_a, team_b]

        def handle_phase(self):
            return "Preseason"

        def save(self):
            pass

        def advance_phase(self):
            pass

    spw.SeasonManager = PreseasonManager
    progress_file = tmp_path / "progress.json"
    monkeypatch.setattr(spw, "PROGRESS_FILE", progress_file)

    win1 = spw.SeasonProgressWindow()
    assert win1.free_agency_button.isEnabled()
    win1.free_agency_button.clicked.emit()

    win2 = spw.SeasonProgressWindow()
    assert not win2.free_agency_button.isEnabled()
    assert win2.training_camp_button.isEnabled()
