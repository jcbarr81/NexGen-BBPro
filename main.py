import os
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from ui.splash_screen import SplashScreen
from ui.theme import DARK_QSS
from ui.version_badge import install_version_badge


def _show_splash_window(window: SplashScreen, app: QApplication) -> None:
    """Present the splash window maximized while keeping Wayland stability."""
    platform = (QGuiApplication.platformName() or "").lower()
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()

    if "wayland" in (platform, session_type):
        # Avoid an initial maximized show that can crash under fractional scaling
        screen = window.screen() or app.primaryScreen()
        if screen:
            window.setGeometry(screen.availableGeometry())
        window.show()

        def _maximize_after_show():
            window.setWindowState(window.windowState() | Qt.WindowState.WindowMaximized)
            window.raise_()
            window.activateWindow()

        QTimer.singleShot(0, _maximize_after_show)
        return

    window.showMaximized()
    window.raise_()
    window.activateWindow()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    install_version_badge(app)
    splash = SplashScreen()
    _show_splash_window(splash, app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
