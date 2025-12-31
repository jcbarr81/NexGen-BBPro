import sys, types, os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
        self.triggered = DummySignal()
    def __getattr__(self, name):
        return Dummy()
    def addItem(self, *args, **kwargs):
        pass
    def clear(self, *args, **kwargs):
        pass
    def setLayout(self, *args, **kwargs):
        pass
    def connect(self, *args, **kwargs):
        pass
    def setFont(self, *args, **kwargs):
        pass
    def exec(self, *args, **kwargs):
        pass
    def setPlainText(self, *args, **kwargs):
        pass
    def setHtml(self, *args, **kwargs):
        pass
    def setReadOnly(self, *args, **kwargs):
        pass
    def setStyleSheet(self, *args, **kwargs):
        pass
    def setMinimumHeight(self, *args, **kwargs):
        pass
    def setWindowTitle(self, *args, **kwargs):
        pass
    def setGeometry(self, *args, **kwargs):
        pass
    def setContentsMargins(self, *args, **kwargs):
        pass
    def addTab(self, *args, **kwargs):
        pass
    def addStretch(self, *args, **kwargs):
        pass
    def setMenuBar(self, *args, **kwargs):
        pass
    def addWidget(self, *args, **kwargs):
        pass
    def addItems(self, *args, **kwargs):
        pass
    def currentItem(self):
        return None
    def setText(self, *args, **kwargs):
        pass
    def warning(self, *args, **kwargs):
        return 0
    def information(self, *args, **kwargs):
        return 0
    def critical(self, *args, **kwargs):
        return 0
    def question(self, *args, **kwargs):
        return 0


class Dialog:
    def __init__(self, *args, **kwargs):
        pass

    def setWindowTitle(self, *args, **kwargs):
        pass

    def setGeometry(self, *args, **kwargs):
        pass

    def exec(self, *args, **kwargs):
        pass

class QAction:
    def __init__(self, *args, **kwargs):
        self.triggered = DummySignal()
    def trigger(self):
        self.triggered.emit()

class QMenu(Dummy):
    def addAction(self, *args, **kwargs):
        return QAction()
    def addMenu(self, *args, **kwargs):
        return QMenu()

class QMenuBar(Dummy):
    def addMenu(self, *args, **kwargs):
        return QMenu()

qtwidgets = types.ModuleType("PyQt6.QtWidgets")
widget_names = [
    'QWidget','QLabel','QVBoxLayout','QTabWidget','QListWidget','QTextEdit','QPushButton',
    'QHBoxLayout','QComboBox','QMessageBox','QGroupBox','QMenuBar','QFormLayout',
    'QSpinBox','QGridLayout','QScrollArea','QLineEdit','QTableWidget','QTableWidgetItem',
    'QMainWindow','QStackedWidget','QFrame','QStatusBar','QToolButton','QSizePolicy','QSpacerItem','QApplication'
]
for name in widget_names:
    setattr(qtwidgets, name, Dummy)
qtwidgets.QMenuBar = QMenuBar
qtwidgets.QMenu = QMenu
qtwidgets.QAction = QAction
qtwidgets.QDialog = Dialog
qtwidgets.__getattr__ = lambda name: Dummy


class QTextEdit(Dummy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._html = ""

    def setHtml(self, html):
        self._html = html

    def setPlainText(self, text):
        self._html = text

    def toHtml(self):
        return self._html


qtwidgets.QTextEdit = QTextEdit

class QListWidgetItem:
    def __init__(self, text):
        self._text = text
        self._data = {}
    def setData(self, role, value):
        self._data[role] = value
    def data(self, role):
        return self._data.get(role)
    def text(self):
        return self._text
qtwidgets.QListWidgetItem = QListWidgetItem

qtcore = types.ModuleType("PyQt6.QtCore")
class Qt:
    pass
qtcore.Qt = Qt
class QPropertyAnimation:
    pass
qtcore.QPropertyAnimation = QPropertyAnimation
class QTimer:
    def __init__(self, *args, **kwargs):
        pass
    def start(self, *args, **kwargs):
        pass
    def stop(self, *args, **kwargs):
        pass
qtcore.QTimer = QTimer
def pyqtSignal(*args, **kwargs):
    return DummySignal()
qtcore.pyqtSignal = pyqtSignal
sys.modules['PyQt6'] = types.ModuleType('PyQt6')
sys.modules['PyQt6.QtWidgets'] = qtwidgets
sys.modules['PyQt6.QtCore'] = qtcore

qtgui = types.ModuleType("PyQt6.QtGui")
class QFont:
    def __init__(self, *args, **kwargs):
        pass
    def setBold(self, *args, **kwargs):
        pass
    def setPointSize(self, *args, **kwargs):
        pass
qtgui.QFont = QFont
qtgui.QPixmap = Dummy
sys.modules['PyQt6.QtGui'] = qtgui

theme_mod = types.ModuleType('ui.theme')
theme_mod._toggle_theme = lambda status_bar=None: None
theme_mod.DARK_QSS = ""
sys.modules['ui.theme'] = theme_mod

# ---- Imports after stubbing ----
sys.modules.pop("ui.owner_dashboard", None)
sys.modules.pop("ui.standings_window", None)
import ui.owner_dashboard as owner_dashboard
import ui.standings_window as standings_window


def test_standings_action_opens_dialog(monkeypatch):
    opened = {}

    class DummyStandings:
        def __init__(self, *a, **k):
            pass
        def exec(self):
            opened["shown"] = True

    monkeypatch.setattr(owner_dashboard, "StandingsWindow", DummyStandings)
    monkeypatch.setattr(owner_dashboard, "show_on_top", lambda w: w.exec())

    def fake_init(self, team_id):
        self.team_id = team_id
        self.standings_action = QAction()
        self.standings_action.triggered.connect(self.open_standings_window)

    monkeypatch.setattr(owner_dashboard.OwnerDashboard, "__init__", fake_init)

    dashboard = owner_dashboard.OwnerDashboard("DRO")
    dashboard.standings_action.trigger()

    assert opened.get("shown")


def test_standings_window_displays_league_and_teams():
    window = standings_window.StandingsWindow()
    html = window.viewer.toHtml()
    assert "USABL" in html
    # Verify at least one team from teams.csv appears in the standings output
    from utils.team_loader import load_teams
    teams = load_teams("data/teams.csv")
    assert teams, "Expected teams to be present in data/teams.csv"
    first = teams[0]
    team_label = f"{first.city} {first.name}"
    assert team_label in html
    assert "<pre>" in html
    assert "<ul>" not in html
