import sys
from PyQt6.QtWidgets import QApplication
from ui.splash_screen import SplashScreen

def main():
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.showMaximized()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
