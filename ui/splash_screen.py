import os
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt

from ui.login_window import LoginWindow

class SplashScreen(QWidget):
    """Initial splash screen displaying the UBL logo and start button."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("UBL")

        layout = QVBoxLayout()
        layout.addStretch()

        logo_label = QLabel()
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "logo",
            "UBL.png",
        )
        logo_label.setPixmap(QPixmap(logo_path))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        layout.addStretch()

        self.login_button = QPushButton("Start Game")
        font = self.login_button.font()
        font.setPointSize(18)
        font.setBold(True)
        self.login_button.setFont(font)
        self.login_button.clicked.connect(self.open_login)
        layout.addWidget(self.login_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add a larger stretch below the button to push it upward for a
        # more balanced appearance on the splash screen.
        layout.addStretch(2)

        self.setLayout(layout)
        self.login_window = None

    def open_login(self):
        """Show the login window and hide the splash screen."""
        self.login_window = LoginWindow()
        self.login_window.show()
        self.hide()
