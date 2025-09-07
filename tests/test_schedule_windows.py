import sys, types, csv
from pathlib import Path

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

# Table-specific stubs
class QTableWidget(Dummy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._items = {}
        self._rows = 0
        self._cols = 0
    def setColumnCount(self, n):
        self._cols = n
    def setRowCount(self, n):
        self._rows = n
    def setHorizontalHeaderLabels(self, labels):
        self._headers = labels
    def setItem(self, row, col, item):
        self._items[(row, col)] = item
    def item(self, row, col):
        return self._items.get((row, col))
    def resizeColumnsToContents(self):
        pass

class QTableWidgetItem:
    def __init__(self, text):
        self._text = text
    def text(self):
        return self._text

qtwidgets = types.ModuleType("PyQt6.QtWidgets")
widget_names = [
    'QWidget','QLabel','QVBoxLayout','QTabWidget','QListWidget','QTextEdit','QPushButton',
    'QHBoxLayout','QComboBox','QMessageBox','QGroupBox','QMenuBar','QDialog','QFormLayout',
    'QSpinBox','QGridLayout','QScrollArea','QLineEdit','QMainWindow','QStackedWidget',
    'QFrame','QStatusBar','QToolButton','QSizePolicy','QSpacerItem','QApplication'
]
for name in widget_names:
    setattr(qtwidgets, name, Dummy)
qtwidgets.QMenuBar = QMenuBar
qtwidgets.QMenu = QMenu
qtwidgets.QAction = QAction
qtwidgets.__getattr__ = lambda name: Dummy
# Provide a simple QTextEdit capable of storing HTML for assertions
class QTextEdit(Dummy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._html = ""

    def setHtml(self, html):
        self._html = html

    def toHtml(self):
        return self._html

    def setPlainText(self, text):
        self._html = text

qtwidgets.QTextEdit = QTextEdit
qtwidgets.QTableWidget = QTableWidget
qtwidgets.QTableWidgetItem = QTableWidgetItem
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
    class ItemDataRole:
        UserRole = 0
qtcore.Qt = Qt
class QPropertyAnimation:
    pass
qtcore.QPropertyAnimation = QPropertyAnimation
sys.modules['PyQt6'] = types.ModuleType('PyQt6')
sys.modules['PyQt6.QtWidgets'] = qtwidgets
sys.modules['PyQt6.QtCore'] = qtcore

theme_mod = types.ModuleType('ui.theme')
theme_mod._toggle_theme = lambda status_bar=None: None
theme_mod.DARK_QSS = ""
sys.modules['ui.theme'] = theme_mod

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

# ---- Imports after stubbing ----
import importlib
import ui.schedule_window as schedule_window
importlib.reload(schedule_window)
import ui.team_schedule_window as team_schedule_window
importlib.reload(team_schedule_window)
import ui.owner_dashboard as owner_dashboard
importlib.reload(owner_dashboard)


def test_schedule_windows_show_data(monkeypatch, tmp_path):
    # prepare schedule csv
    schedule_path = tmp_path / 'schedule.csv'
    with schedule_path.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=['date','home','away','result','boxscore'])
        writer.writeheader()
        writer.writerow({'date':'2024-04-01','home':'A','away':'B','result':'W 3-2','boxscore':''})
        writer.writerow({'date':'2024-04-02','home':'C','away':'A','result':'L 1-2','boxscore':''})

    monkeypatch.setattr(schedule_window, 'SCHEDULE_FILE', schedule_path)
    monkeypatch.setattr(team_schedule_window, 'SCHEDULE_FILE', schedule_path)
    monkeypatch.setattr(owner_dashboard, 'ScheduleWindow', schedule_window.ScheduleWindow)
    monkeypatch.setattr(owner_dashboard, 'TeamScheduleWindow', team_schedule_window.TeamScheduleWindow)

    opened = {}

    orig_sched_init = schedule_window.ScheduleWindow.__init__
    def spy_sched_init(self, *a, **k):
        orig_sched_init(self, *a, **k)
        opened['league'] = self
    monkeypatch.setattr(schedule_window.ScheduleWindow, '__init__', spy_sched_init)

    orig_team_init = team_schedule_window.TeamScheduleWindow.__init__
    def spy_team_init(self, team_id, *a, **k):
        orig_team_init(self, team_id, *a, **k)
        opened['team'] = self
    monkeypatch.setattr(team_schedule_window.TeamScheduleWindow, '__init__', spy_team_init)

    def fake_exec(self):
        opened.setdefault('executed', []).append(self)
    monkeypatch.setattr(schedule_window.ScheduleWindow, 'exec', fake_exec)
    monkeypatch.setattr(team_schedule_window.TeamScheduleWindow, 'exec', fake_exec)

    def fake_init(self, team_id):
        self.team_id = team_id
        self.schedule_action = QAction()
        self.schedule_action.triggered.connect(self.open_schedule_window)
        self.team_schedule_action = QAction()
        self.team_schedule_action.triggered.connect(self.open_team_schedule_window)
    monkeypatch.setattr(owner_dashboard.OwnerDashboard, '__init__', fake_init)

    dashboard = owner_dashboard.OwnerDashboard('A')
    dashboard.schedule_action.trigger()
    league = opened['league']
    assert league.viewer.item(0,0).text() == '2024-04-01'
    assert league.viewer.item(0,1).text() == 'B'
    assert league.viewer.item(0,2).text() == 'A'

    dashboard.team_schedule_action.trigger()
    team = opened['team']
    texts = []
    for r in range(6):
        for c in range(7):
            item = team.viewer.item(r, c)
            if item:
                texts.append(item.text())
    assert any('vs B' in t and '1' in t and 'W 3-2' in t for t in texts)
    assert any('at C' in t and '2' in t and 'L 1-2' in t for t in texts)


def test_owner_dashboard_stats_windows(monkeypatch):
    from types import SimpleNamespace

    called = []

    class DummyTabs:
        def __init__(self):
            self.idx = None

        def setCurrentIndex(self, i):
            self.idx = i

    class DummyWindow:
        def __init__(self, *a, **k):
            self.tabs = DummyTabs()

        def exec(self):
            called.append(self.tabs.idx)

    monkeypatch.setattr(owner_dashboard, 'TeamStatsWindow', DummyWindow)

    def fake_init(self, team_id):
        self.team_id = team_id
        self.players = {}
        self.roster = SimpleNamespace()
        self.team = SimpleNamespace(season_stats={})

    monkeypatch.setattr(owner_dashboard.OwnerDashboard, '__init__', fake_init)

    dash = owner_dashboard.OwnerDashboard('X')
    dash.open_team_stats_window()
    dash.open_player_stats_window()

    assert called == [2, 0]
