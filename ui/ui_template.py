import sys
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolButton, QStackedWidget, QLabel, QFrame, QPushButton,
    QSizePolicy, QStatusBar, QSpacerItem
)

# ------------------------------------------------------------
# Theme toggles
# ------------------------------------------------------------

LIGHT_QSS = """
/* App */
QWidget {
    background: #f7f8fb;
    color: #0f2545;
    font-family: 'Segoe UI', 'Noto Sans', Arial;
    font-size: 14px;
}

/* Sidebar (dugout) */
#Sidebar {
    background: #0f2545; /* deep navy */
    border: none;
}
#Sidebar QLabel {
    color: #f1f5ff;
    font-weight: 600;
    padding: 8px 10px;
    letter-spacing: .5px;
}
#NavButton {
    color: #e7efff;
    background: transparent;
    padding: 10px 14px;
    margin: 4px 8px;
    border-radius: 10px;
    text-align: left;
}
#NavButton:hover { background: #1b3b6b; }
#NavButton:checked {
    background: #1b4d89;
    border: 1px solid #2b66b8;
    color: white;
}

/* Header (scoreboard strip) */
#Header {
    background: white;
    border-bottom: 1px solid #e6e9f2;
}
#Title {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: .5px;
}
#Scoreboard {
    background: #0f2545;
    color: #f6f8ff;
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 700;
}

/* Cards and content */
QFrame#Card {
    background: white;
    border: 1px solid #e9edf5;
    border-radius: 14px;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #0f2545;
}

/* Buttons */
QPushButton#Primary {
    background: #1b4d89;  /* primary blue */
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#Primary:hover { background: #205aa0; }
QPushButton#Primary:pressed { background: #17487a; }

QPushButton#Success {
    background: #2f9e44;  /* "Play ball" green */
    color: white;
    border: none;
    padding: 12px 18px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#Success:hover { background: #27903c; }
QPushButton#Success:pressed { background: #237f35; }

QStatusBar { background: #ffffff; border-top: 1px solid #e6e9f2; }
"""

DARK_QSS = """
QWidget {
    background: #0f1623;
    color: #e6ecfa;
    font-family: 'Segoe UI', 'Noto Sans', Arial;
    font-size: 14px;
}
#Sidebar {
    background: #0b1222;
}
#Sidebar QLabel { color: #dbe6ff; }
#NavButton {
    color: #cfe0ff;
    background: transparent;
    padding: 10px 14px;
    margin: 4px 8px;
    border-radius: 10px;
}
#NavButton:hover { background: #132645; }
#NavButton:checked {
    background: #19345f;
    border: 1px solid #2a4c8e;
    color: white;
}
#Header {
    background: #111a2b;
    border-bottom: 1px solid #1b2943;
}
#Title { color: #eaf1ff; }
#Scoreboard {
    background: #0b1222;
    color: #eaf1ff;
    border: 1px solid #1b2943;
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 700;
}
QFrame#Card {
    background: #121b2d;
    border: 1px solid #1b2943;
    border-radius: 14px;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #e6ecfa;
}
QPushButton#Primary {
    background: #1b4d89;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#Primary:hover { background: #205aa0; }
QPushButton#Primary:pressed { background: #17487a; }
QPushButton#Success {
    background: #2f9e44;
    color: white;
    border: none;
    padding: 12px 18px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#Success:hover { background: #27903c; }
QPushButton#Success:pressed { background: #237f35; }
QStatusBar { background: #0f1623; border-top: 1px solid #1b2943; }
"""

# ------------------------------------------------------------
# Small building blocks
# ------------------------------------------------------------

class NavButton(QToolButton):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName("NavButton")
        # Emoji icons keep dependencies light; swap for SVGs if you prefer
        self.setText(text)  # e.g., "⚾  Dashboard"
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(18, 18, 18, 18)
        self.layout().setSpacing(10)

def section_title(text):
    lbl = QLabel(text)
    lbl.setObjectName("SectionTitle")
    return lbl

def spacer(h=1, v=1):
    return QSpacerItem(h, v, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        # Row of quick cards
        row = QHBoxLayout()
        row.setSpacing(18)

        c1 = Card()
        c1.layout().addWidget(section_title("Today’s Slate"))
        c1.layout().addWidget(QLabel("• Exhibition: Knights @ Admirals\n• Scrimmage: Monarchs @ Pilots"))
        c1.layout().addStretch()

        c2 = Card()
        c2.layout().addWidget(section_title("Admin Shortcuts"))
        for text in ("Review Trades", "Create League", "Season Progress"):
            btn = QPushButton(f"⚾  {text}")
            btn.setObjectName("Primary")
            c2.layout().addWidget(btn)
        c2.layout().addStretch()

        c3 = Card()
        c3.layout().addWidget(section_title("League Health"))
        c3.layout().addWidget(QLabel("Teams: 30\nPlayers: 900\nOpen Tickets: 3"))
        c3.layout().addStretch()

        row.addWidget(c1)
        row.addWidget(c2)
        row.addWidget(c3)

        big = Card()
        big.layout().addWidget(section_title("Game Control"))
        play = QPushButton("Play Ball – Simulate Exhibition Game")
        play.setObjectName("Success")
        play.setMinimumHeight(48)
        big.layout().addWidget(play)

        root.addLayout(row)
        root.addWidget(big)
        root.addStretch()

class LeaguePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        card = Card()
        card.layout().addWidget(section_title("League Management"))
        card.layout().addWidget(QLabel("Create leagues, edit rules, schedule seasons."))
        card.layout().addWidget(QPushButton("New League", objectName="Primary"))
        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()

class TeamsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        card = Card()
        card.layout().addWidget(section_title("Team Management"))
        card.layout().addWidget(QLabel("Manage rosters, depth charts, and finances."))
        card.layout().addWidget(QPushButton("Open Team Directory", objectName="Primary"))
        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()

class UsersPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        card = Card()
        card.layout().addWidget(section_title("User Management"))
        card.layout().addWidget(QLabel("Invites, roles, and permissions for your GMs."))
        card.layout().addWidget(QPushButton("Add User", objectName="Primary"))
        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()

class UtilitiesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        card = Card()
        card.layout().addWidget(section_title("Utilities"))
        card.layout().addWidget(QLabel("Import/export data, backups, and tools."))
        card.layout().addWidget(QPushButton("Open Utilities", objectName="Primary"))
        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()

# ------------------------------------------------------------
# Main Window
# ------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Commissioner's Office – Admin Dashboard")
        self.resize(1100, 720)

        # Central area: sidebar + content
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar (dugout)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(10, 12, 10, 12)
        side.setSpacing(6)

        brand = QLabel("⚾  Commissioner")
        brand.setStyleSheet("font-weight:900; font-size:16px;")
        side.addWidget(brand)

        self.btn_dashboard = NavButton("  Dashboard")
        self.btn_league = NavButton("  League")
        self.btn_teams = NavButton("  Teams")
        self.btn_users = NavButton("  Users")
        self.btn_utils = NavButton("  Utilities")

        # Make them mutually exclusive
        for b in (self.btn_dashboard, self.btn_league, self.btn_teams, self.btn_users, self.btn_utils):
            side.addWidget(b)

        side.addStretch()
        side.addWidget(QLabel("  Settings"))
        self.btn_settings = NavButton("  Preferences")
        side.addWidget(self.btn_settings)

        # Header (scoreboard)
        header = QFrame()
        header.setObjectName("Header")
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 10, 18, 10)
        h.setSpacing(12)

        title = QLabel("Welcome to the Admin Dashboard")
        title.setObjectName("Title")
        title.setFont(QFont(title.font().family(), 11, weight=QFont.Weight.ExtraBold))
        h.addWidget(title)
        h.addStretch()

        self.scoreboard = QLabel("Top 1st • 0–0 • No Outs")
        self.scoreboard.setObjectName("Scoreboard")
        h.addWidget(self.scoreboard, alignment=Qt.AlignmentFlag.AlignRight)

        # Stacked content
        self.stack = QStackedWidget()
        self.pages = {
            "dashboard": DashboardPage(),
            "league": LeaguePage(),
            "teams": TeamsPage(),
            "users": UsersPage(),
            "utils": UtilitiesPage(),
        }
        for p in self.pages.values():
            self.stack.addWidget(p)

        # Right side: header + stacked pages
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        rv.addWidget(header)
        rv.addWidget(self.stack)

        root.addWidget(sidebar)
        root.addWidget(right)
        root.setStretchFactor(right, 1)
        sidebar.setFixedWidth(210)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        # Menu
        self._build_menu()

        # Signals
        self.btn_dashboard.clicked.connect(lambda: self._go("dashboard"))
        self.btn_league.clicked.connect(lambda: self._go("league"))
        self.btn_teams.clicked.connect(lambda: self._go("teams"))
        self.btn_users.clicked.connect(lambda: self._go("users"))
        self.btn_utils.clicked.connect(lambda: self._go("utils"))
        self.btn_settings.clicked.connect(self._toggle_theme)

        # Default selection
        self.btn_dashboard.setChecked(True)
        self._go("dashboard")

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("&View")
        theme_action = QAction("Toggle Dark Mode", self)
        theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_action)

    def _go(self, key):
        idx = list(self.pages.keys()).index(key)
        self.stack.setCurrentIndex(idx)
        self.statusBar().showMessage(f"Ready • {key.capitalize()}")

    def _toggle_theme(self):
        # swap app-wide style between light and dark
        current = self.parent().styleSheet() if self.parent() else self.styleSheet()
        # detect by a token present in each sheet
        is_dark = "0f1623" in QApplication.instance().styleSheet()
        if is_dark:
            QApplication.instance().setStyleSheet(LIGHT_QSS)
            self.statusBar().showMessage("Light theme")
        else:
            QApplication.instance().setStyleSheet(DARK_QSS)
            self.statusBar().showMessage("Dark theme")

# ------------------------------------------------------------
# Run
# ------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_QSS)  # start in light; toggle with View > Toggle Dark Mode
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
