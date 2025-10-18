from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt
try:  # Qt timer is optional under our test stubs
    from PyQt6.QtCore import QTimer
except ImportError:  # pragma: no cover - exercised via stubbed tests
    class QTimer:  # type: ignore[override]
        @staticmethod
        def singleShot(_msec, callback):
            if callable(callback):
                callback()
import sys
import importlib

import bcrypt

from utils.path_utils import get_base_dir
from ui.theme import DARK_QSS
from ui.window_utils import show_on_top
from ui.version_badge import install_version_badge

# Determine the path to the users file in a cross-platform way
USER_FILE = get_base_dir() / "data" / "users.txt"

class LoginWindow(QWidget):
    def __init__(self, splash=None):
        super().__init__()
        self.setWindowTitle("UBL Login")

        # Keep a reference to the splash screen so it can be closed after
        # successful authentication.
        self.splash = splash

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.username_input.setFocus()

        self.login_button = QPushButton("Login")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.handle_login)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        self.setLayout(layout)

        # Connect returnPressed signal to login
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)

        self.dashboard = None
        self._center_pending = True
        self._center_scheduled = False

    def showEvent(self, event):
        super().showEvent(event)
        self._center_pending = True
        self._center_on_screen()
        for delay in (20, 80, 160):
            QTimer.singleShot(delay, self._center_on_screen)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._center_pending and not self._center_scheduled:
            self._center_scheduled = True
            QTimer.singleShot(0, self._center_on_screen)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not USER_FILE.exists():
            QMessageBox.critical(self, "Error", "User file not found.")
            return

        with USER_FILE.open("r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) != 4:
                    continue
                file_user, file_pass, role, team_id = parts
                if file_user != username:
                    continue
                hashed_match = False
                try:
                    hashed_match = bcrypt.checkpw(
                        password.encode("utf-8"), file_pass.encode("utf-8")
                    )
                except ValueError:
                    hashed_match = False
                if hashed_match or password == file_pass:
                    self.accept_login(role, team_id)
                    return

        QMessageBox.warning(self, "Login Failed", "Invalid username or password.")

    def accept_login(self, role, team_id):
        if role == "admin":
            mod = importlib.import_module("ui.admin_dashboard")
            dash_cls = getattr(mod, "AdminDashboard", None) or getattr(
                mod, "MainWindow", None
            )
            if dash_cls is None:
                QMessageBox.warning(self, "Error", "Admin dashboard not found.")
                return
            self.dashboard = dash_cls()
        elif role == "owner":
            mod = importlib.import_module("ui.owner_dashboard")
            dash_cls = getattr(mod, "OwnerDashboard", None) or getattr(
                mod, "MainWindow", None
            )
            if dash_cls is None:
                QMessageBox.warning(self, "Error", "Owner dashboard not found.")
                return
            self.dashboard = dash_cls(team_id)
        else:
            QMessageBox.warning(self, "Error", "Unrecognized role.")
            return

        # When the dashboard window is closed, bring the splash screen back to
        # the front and re-enable the start button so another session can be
        # launched.
        self.dashboard.closeEvent = self.dashboard_closed

        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_QSS)
            install_version_badge(app)

        show_on_top(self.dashboard)

        # Keep the splash screen visible while the dashboard is open so it
        # behaves the same way it does when the login window is shown.  This
        # allows the splash screen to remain in the background while users
        # interact with the dashboard.
        # Close the login window now that the dashboard is displayed.
        self.close()

    def dashboard_closed(self, event):
        """Handle a dashboard being closed by returning focus to the splash."""
        if self.splash:
            # Restore the splash screen when the dashboard closes.
            self.splash.show()
            self.splash.raise_()
            self.splash.activateWindow()
            self.splash.login_button.setEnabled(True)
        event.accept()

    def closeEvent(self, event):
        """Ensure the splash button is re-enabled if login is cancelled."""
        if self.dashboard is None and self.splash:
            self.splash.login_button.setEnabled(True)
        event.accept()

    def _center_on_screen(self) -> None:
        """Center the login window on the active screen."""
        self._center_scheduled = False
        screen = None

        handle_fn = getattr(self, "windowHandle", None)
        if callable(handle_fn):
            handle = handle_fn()
            screen_fn = getattr(handle, "screen", None) if handle is not None else None
            if callable(screen_fn):
                screen = screen_fn()

        if screen is None:
            screen_fn = getattr(self, "screen", None)
            if callable(screen_fn):
                screen = screen_fn()

        if screen is None:
            instance_fn = getattr(QApplication, "instance", None)
            if callable(instance_fn):
                app = instance_fn()
                if app is not None:
                    primary_fn = getattr(app, "primaryScreen", None)
                    if callable(primary_fn):
                        screen = primary_fn()

        if screen is None:
            try:
                from PyQt6.QtGui import QGuiApplication  # type: ignore
            except ImportError:
                QGuiApplication = None  # type: ignore[assignment]
            if QGuiApplication is not None:
                screen = QGuiApplication.primaryScreen()

        if screen is None:
            return

        available = getattr(screen, "availableGeometry", lambda: None)()
        if available is None:
            return
        avail_center = getattr(available, "center", lambda: None)()

        is_visible = getattr(self, "isVisible", lambda: False)()
        if is_visible:
            frame = getattr(self, "frameGeometry", lambda: None)()
            if frame is not None and getattr(frame, "isValid", lambda: False)():
                width = getattr(frame, "width", lambda: 0)()
                height = getattr(frame, "height", lambda: 0)()
                if width > 0 and height > 0 and avail_center is not None:
                    target_x = int(getattr(avail_center, "x", lambda: 0)() - width / 2)
                    target_y = int(getattr(avail_center, "y", lambda: 0)() - height / 2)
                    current_top_left = getattr(frame, "topLeft", lambda: None)()
                    current_x = getattr(current_top_left, "x", lambda: target_x)()
                    current_y = getattr(current_top_left, "y", lambda: target_y)()
                    if abs(current_x - target_x) <= 1 and abs(current_y - target_y) <= 1:
                        self._center_pending = False
                        return
                    self.move(target_x, target_y)
                    return

        hint = getattr(self, "sizeHint", lambda: None)()
        if hint is None or not getattr(hint, "isValid", lambda: False)():
            adjust = getattr(self, "adjustSize", None)
            if callable(adjust):
                adjust()
            hint = getattr(self, "sizeHint", lambda: None)()

        if hint is None:
            return

        width = getattr(hint, "width", lambda: 0)()
        height = getattr(hint, "height", lambda: 0)()
        if width <= 0 or height <= 0:
            return

        avail_x = getattr(available, "x", lambda: 0)()
        avail_y = getattr(available, "y", lambda: 0)()
        avail_w = getattr(available, "width", lambda: width)()
        avail_h = getattr(available, "height", lambda: height)()

        x = int(avail_x + max(0, (avail_w - width) / 2))
        y = int(avail_y + max(0, (avail_h - height) / 2))

        set_geometry = getattr(self, "setGeometry", None)
        if callable(set_geometry):
            set_geometry(x, y, width, height)
        else:
            move = getattr(self, "move", None)
            resize = getattr(self, "resize", None)
            if callable(resize):
                resize(width, height)
            if callable(move):
                move(x, y)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    install_version_badge(app)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
