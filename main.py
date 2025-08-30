import sys
from PyQt6.QtWidgets import QApplication

from ui.splash_screen import SplashScreen
from ui.theme import LIGHT_QSS

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_QSS)
    splash = SplashScreen()
    splash.showMaximized()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
