import sys
from PyQt6.QtWidgets import QApplication

from ui.splash_screen import SplashScreen
from ui.theme import DARK_QSS
from ui.version_badge import install_version_badge


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    install_version_badge(app)
    splash = SplashScreen()
    splash.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
