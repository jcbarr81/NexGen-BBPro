import sys, types
from enum import Enum
from types import SimpleNamespace

# ---- Stub PyQt6 modules ----
class Dummy:
    def __init__(self, *args, **kwargs):
        pass
    def __getattr__(self, name):
        return Dummy()
    def addItem(self, *args, **kwargs):
        pass
    def clear(self, *args, **kwargs):
        pass
    def setLayout(self, *args, **kwargs):
        pass
    def clicked(self, *args, **kwargs):
        return Dummy()
    def connect(self, *args, **kwargs):
        pass
    def setFont(self, *args, **kwargs):
        pass
    def exec(self, *args, **kwargs):
        pass

qtwidgets = types.ModuleType("PyQt6.QtWidgets")
widget_names = [
    'QWidget','QLabel','QVBoxLayout','QTabWidget','QListWidget','QTextEdit','QPushButton',
    'QHBoxLayout','QComboBox','QMessageBox','QGroupBox','QMenuBar','QDialog','QFormLayout',
    'QSpinBox','QGridLayout','QScrollArea','QLineEdit','QTableWidget','QTableWidgetItem'
]
for name in widget_names:
    setattr(qtwidgets, name, Dummy)

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
class ItemDataRole(Enum):
    UserRole = 0
class Qt:
    ItemDataRole = ItemDataRole
qtcore.Qt = Qt
class QPropertyAnimation:  # needed for lineup_editor import
    pass
qtcore.QPropertyAnimation = QPropertyAnimation

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

sys.modules['PyQt6'] = types.ModuleType('PyQt6')
sys.modules['PyQt6.QtWidgets'] = qtwidgets
sys.modules['PyQt6.QtCore'] = qtcore
sys.modules['PyQt6.QtGui'] = qtgui

# ---- Imports after stubbing ----
import ui.owner_dashboard as owner_dashboard
import ui.position_players_dialog as pp_dialog
from models.pitcher import Pitcher
from models.player import Player

# Dummy self objects providing required methods
od_helper = SimpleNamespace(calculate_age=lambda _: 0)
ppd_helper = SimpleNamespace(_calculate_age=lambda _: 0)

def test_pitcher_uses_pitching_stats_even_if_primary_not_pitcher():
    pitcher = Pitcher(
        player_id='p1', first_name='Pitch', last_name='Er', birthdate='1990-01-01',
        height=72, weight=180, bats='R', primary_position='LF', other_positions=[], gf=10,
        arm=60, endurance=50, control=40, role='SP'
    )
    item_od = owner_dashboard.OwnerDashboard._make_player_item(od_helper, pitcher)
    item_ppd = pp_dialog.PositionPlayersDialog._make_player_item(ppd_helper, pitcher)
    for item in (item_od, item_ppd):
        text = item.text()
        assert 'AS:' in text and 'EN:' in text and 'CO:' in text
        assert 'CH:' not in text

def test_hitter_uses_hitting_stats_even_if_primary_pitcher():
    hitter = Player(
        player_id='h1', first_name='Hit', last_name='Ter', birthdate='1991-02-02',
        height=70, weight=175, bats='L', primary_position='P', other_positions=[], gf=20,
        ch=55, ph=65, sp=75
    )
    item_od = owner_dashboard.OwnerDashboard._make_player_item(od_helper, hitter)
    item_ppd = pp_dialog.PositionPlayersDialog._make_player_item(ppd_helper, hitter)
    for item in (item_od, item_ppd):
        text = item.text()
        assert 'CH:' in text and 'PH:' in text and 'SP:' in text
        assert 'AS:' not in text and 'EN:' not in text and 'CO:' not in text
