import os, sys, types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

class DummySignal:
    def __init__(self):
        self._slot = None
    def connect(self, slot):
        self._slot = slot
    def emit(self):
        if self._slot:
            self._slot()

class QWidget:
    def __init__(self, *args, **kwargs):
        pass
    def setLayout(self, *args, **kwargs):
        pass
    def setWindowTitle(self, *args, **kwargs):
        pass
    def setGeometry(self, *args, **kwargs):
        pass
    def close(self):
        pass
    def show(self):
        pass
    def raise_(self):
        pass
    def activateWindow(self):
        pass

class QLabel:
    def __init__(self, *args, **kwargs):
        pass

class QLineEdit:
    class EchoMode:
        Password = 0
    def __init__(self):
        self._text = ""
        self.returnPressed = DummySignal()
    def setPlaceholderText(self, text):
        pass
    def setEchoMode(self, mode):
        pass
    def setFocus(self):
        pass
    def text(self):
        return self._text
    def setText(self, text):
        self._text = text

class QPushButton:
    def __init__(self, *args, **kwargs):
        self.clicked = DummySignal()
    def setDefault(self, val):
        pass
    def setEnabled(self, val):
        pass

class QVBoxLayout:
    def addWidget(self, *args, **kwargs):
        pass

class QMessageBox:
    @staticmethod
    def critical(*args, **kwargs):
        pass
    @staticmethod
    def warning(*args, **kwargs):
        pass

class QApplication:
    def __init__(self, *args, **kwargs):
        pass

qtwidgets = types.ModuleType("PyQt6.QtWidgets")
qtwidgets.QApplication = QApplication
qtwidgets.QWidget = QWidget
qtwidgets.QLabel = QLabel
qtwidgets.QLineEdit = QLineEdit
qtwidgets.QPushButton = QPushButton
qtwidgets.QVBoxLayout = QVBoxLayout
qtwidgets.QMessageBox = QMessageBox
sys.modules['PyQt6'] = types.ModuleType('PyQt6')
sys.modules['PyQt6.QtWidgets'] = qtwidgets

qtcore = types.ModuleType("PyQt6.QtCore")
class Qt:
    class AlignmentFlag:
        AlignCenter = 0
qtcore.Qt = Qt
sys.modules['PyQt6.QtCore'] = qtcore

admin_mod = types.ModuleType("ui.admin_dashboard")
class AdminDashboard:
    def __init__(self, *args, **kwargs):
        pass
admin_mod.AdminDashboard = AdminDashboard
sys.modules['ui.admin_dashboard'] = admin_mod

owner_mod = types.ModuleType("ui.owner_dashboard")
class OwnerDashboard:
    def __init__(self, *args, **kwargs):
        pass
owner_mod.OwnerDashboard = OwnerDashboard
sys.modules['ui.owner_dashboard'] = owner_mod

import bcrypt
from ui import login_window

def test_login_plain_and_hashed(tmp_path):
    user_file = tmp_path / "users.txt"
    hashed = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode()
    user_file.write_text(
        f"admin,pass,admin,\nuser,{hashed},owner,team\n"
    )
    login_window.USER_FILE = user_file

    win = login_window.LoginWindow()
    result = {}
    def accept(role, team_id):
        result['role'] = role
        result['team_id'] = team_id
    win.accept_login = accept

    win.username_input.setText("admin")
    win.password_input.setText("pass")
    win.handle_login()
    assert result == {'role': 'admin', 'team_id': ''}

    result.clear()
    win.username_input.setText("user")
    win.password_input.setText("pw")
    win.handle_login()
    assert result == {'role': 'owner', 'team_id': 'team'}
