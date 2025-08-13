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
    'QSpinBox','QGridLayout','QScrollArea','QLineEdit'
]
for name in widget_names:
    setattr(qtwidgets, name, Dummy)
qtwidgets.QMenuBar = QMenuBar
qtwidgets.QMenu = QMenu
qtwidgets.QAction = QAction
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
import ui.owner_dashboard as owner_dashboard
importlib.reload(owner_dashboard)


def test_schedule_action_opens_dialog_and_populates_table(monkeypatch):
    opened = {}

    orig_init = schedule_window.ScheduleWindow.__init__
    def spy_init(self, *a, **k):
        orig_init(self, *a, **k)
        opened['window'] = self
    monkeypatch.setattr(schedule_window.ScheduleWindow, '__init__', spy_init)

    def fake_exec(self):
        opened['executed'] = True
    monkeypatch.setattr(schedule_window.ScheduleWindow, 'exec', fake_exec)

    def fake_init(self, team_id):
        self.team_id = team_id
        self.schedule_action = QAction()
        self.schedule_action.triggered.connect(self.open_schedule_window)
    monkeypatch.setattr(owner_dashboard.OwnerDashboard, '__init__', fake_init)

    dashboard = owner_dashboard.OwnerDashboard('DRO')
    dashboard.schedule_action.trigger()

    assert opened.get('executed')
    window = opened['window']
    assert window.table.item(0, 0).text() == '2024-04-01'
    assert window.table.item(0, 1).text() == 'Team A vs Team B'

