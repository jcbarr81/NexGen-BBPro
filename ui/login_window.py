from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
import sys

import bcrypt

from utils.path_utils import get_base_dir

from ui.admin_dashboard import AdminDashboard
from ui.owner_dashboard import OwnerDashboard

# Determine the path to the users file in a cross-platform way
USER_FILE = get_base_dir() / "data" / "users.txt"

class LoginWindow(QWidget):
    def __init__(self, splash=None):
        super().__init__()
        self.setWindowTitle("UBL Login")
        self.setGeometry(100, 100, 300, 150)

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
            self.dashboard = AdminDashboard()
        elif role == "owner":
            self.dashboard = OwnerDashboard(team_id)
        else:
            QMessageBox.warning(self, "Error", "Unrecognized role.")
            return

        # When the dashboard window is closed, bring the splash screen back to
        # the front and re-enable the start button so another session can be
        # launched.
        self.dashboard.closeEvent = self.dashboard_closed

        # Show the dashboard at its default size rather than maximized so it
        # doesn't dominate the entire screen.
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()


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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
