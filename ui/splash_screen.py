from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QEvent

from ui.login_window import LoginWindow
from utils.path_utils import get_base_dir
from ui.window_utils import show_on_top, set_all_on_top

class SplashScreen(QWidget):
    """Initial splash screen displaying the NexGen logo and start button."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NexGen BBPro")

        layout = QVBoxLayout()
        layout.addStretch()

        logo_label = QLabel()
        logo_path = get_base_dir() / "logo" / "NexGen.png"
        logo_label.setPixmap(QPixmap(str(logo_path)))
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
        """Show the login window while keeping the splash visible."""
        # Disable the button to prevent spawning multiple login windows
        self.login_button.setEnabled(False)

        self.login_window = LoginWindow(self)
        show_on_top(self.login_window)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            set_all_on_top(not self.isMinimized())
        super().changeEvent(event)
