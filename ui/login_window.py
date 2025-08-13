from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox
)
import sys
import os

from ui.admin_dashboard import AdminDashboard
from ui.owner_dashboard import OwnerDashboard

# Determine the path to the users file in a cross-platform way
USER_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "users.txt")
)

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UBL Login")
        self.setGeometry(100, 100, 300, 150)

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

        if not os.path.exists(USER_FILE):
            QMessageBox.critical(self, "Error", "User file not found.")
            return

        with open(USER_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) != 4:
                    continue
                file_user, file_pass, role, team_id = parts
                if file_user == username and file_pass == password:
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

        # Display the dashboard in a maximized window so standard window
        # controls (minimize, maximize, close) are available.
        self.dashboard.showMaximized()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
