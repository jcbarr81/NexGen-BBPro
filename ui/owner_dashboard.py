from __future__ import annotations

from datetime import datetime
from typing import Dict

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QFrame,
    QStatusBar,
    QMessageBox,
    QListWidgetItem,
)

from .components import NavButton
from .theme import _toggle_theme
from .roster_page import RosterPage
from .transactions_page import TransactionsPage
from .schedule_page import SchedulePage
from .lineup_editor import LineupEditor
from .pitching_editor import PitchingEditor
from .position_players_dialog import PositionPlayersDialog
from .transactions_window import TransactionsWindow
from .trade_dialog import TradeDialog
from .standings_window import StandingsWindow
from .schedule_window import ScheduleWindow
from .team_schedule_window import TeamScheduleWindow
from .league_stats_window import LeagueStatsWindow
from .league_leaders_window import LeagueLeadersWindow
from utils.roster_loader import load_roster
from utils.player_loader import load_players_from_csv
from utils.free_agent_finder import find_free_agents
from utils.pitcher_role import get_role
from utils.team_loader import load_teams


class OwnerDashboard(QMainWindow):
    """Owner-facing dashboard with sidebar navigation."""

    def __init__(self, team_id: str):
        super().__init__()
        self.team_id = team_id
        self.players: Dict[str, object] = {
            p.player_id: p for p in load_players_from_csv("data/players.csv")
        }
        self.roster = load_roster(team_id)

        self.setWindowTitle(f"Owner Dashboard - {team_id}")
        self.resize(1100, 720)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(10, 12, 10, 12)
        side.setSpacing(6)

        brand = QLabel(f"⚾  {team_id} Owner")
        brand.setStyleSheet("font-weight:900; font-size:16px;")
        side.addWidget(brand)

        self.btn_roster = NavButton("  Roster")
        self.btn_transactions = NavButton("  Transactions")
        self.btn_league = NavButton("  League")

        for b in (self.btn_roster, self.btn_transactions, self.btn_league):
            side.addWidget(b)

        side.addStretch()
        self.btn_settings = NavButton("  Toggle Theme")
        self.btn_settings.clicked.connect(lambda: _toggle_theme(self.statusBar()))
        side.addWidget(self.btn_settings)

        # Header
        header = QFrame()
        header.setObjectName("Header")
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 10, 18, 10)
        h.setSpacing(12)

        title = QLabel("Team Dashboard")
        title.setObjectName("Title")
        title.setFont(QFont(title.font().family(), 11, weight=QFont.Weight.ExtraBold))
        h.addWidget(title)
        h.addStretch()
        self.scoreboard = QLabel("Ready")
        self.scoreboard.setObjectName("Scoreboard")
        h.addWidget(self.scoreboard, alignment=Qt.AlignmentFlag.AlignRight)

        # Stacked pages
        self.stack = QStackedWidget()
        self.pages = {
            "roster": RosterPage(self),
            "transactions": TransactionsPage(self),
            "league": SchedulePage(self),
        }
        for p in self.pages.values():
            self.stack.addWidget(p)

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

        self._build_menu()

        # Navigation signals
        self.btn_roster.clicked.connect(lambda: self._go("roster"))
        self.btn_transactions.clicked.connect(lambda: self._go("transactions"))
        self.btn_league.clicked.connect(lambda: self._go("league"))
        self.btn_roster.setChecked(True)
        self._go("roster")

        # Expose actions for tests
        self.schedule_action = QAction(self)
        self.schedule_action.triggered.connect(self.open_schedule_window)
        self.team_schedule_action = QAction(self)
        self.team_schedule_action.triggered.connect(self.open_team_schedule_window)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("&View")
        theme_action = QAction("Toggle Dark Mode", self)
        theme_action.triggered.connect(lambda: _toggle_theme(self.statusBar()))
        view_menu.addAction(theme_action)

    def _go(self, key: str) -> None:
        idx = list(self.pages.keys()).index(key)
        self.stack.setCurrentIndex(idx)
        self.statusBar().showMessage(f"Ready • {key.capitalize()}")

    # ---------- Actions used by pages ----------
    def open_lineup_editor(self) -> None:
        LineupEditor(self.team_id).exec()

    def open_pitching_editor(self) -> None:
        PitchingEditor(self.team_id).exec()

    def open_position_players_dialog(self) -> None:
        PositionPlayersDialog(self.players, self.roster).exec()

    def open_transactions_page(self) -> None:
        TransactionsWindow().exec()

    def open_trade_dialog(self) -> None:
        TradeDialog(self.team_id, self).exec()

    def sign_free_agent(self) -> None:
        try:
            free_agents = find_free_agents(self.players, self.roster)
            if not free_agents:
                QMessageBox.information(self, "Free Agents", "No free agents available to sign.")
                return
            pid = free_agents[0]
            self.roster.act.append(pid)
            QMessageBox.information(self, "Free Agents", f"Signed free agent: {pid}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to sign free agent: {e}")

    def open_standings_window(self) -> None:
        StandingsWindow(self).exec()

    def open_schedule_window(self) -> None:
        ScheduleWindow(self).exec()

    def open_team_schedule_window(self) -> None:
        if not getattr(self, "team_id", None):
            QMessageBox.warning(self, "Error", "Team information not available.")
            return
        TeamScheduleWindow(self.team_id, self).exec()

    def open_league_stats_window(self) -> None:
        teams = load_teams()
        LeagueStatsWindow(teams, self.players.values(), self).exec()

    def open_league_leaders_window(self) -> None:
        LeagueLeadersWindow(self.players.values(), self).exec()

    # ---------- Utilities ----------
    def calculate_age(self, birthdate_str: str):
        try:
            birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        except Exception:
            return "?"

    def _make_player_item(self, p):
        age = self.calculate_age(p.birthdate)
        role = get_role(p)
        if role:
            core = f"AS:{getattr(p, 'arm', 0)} EN:{getattr(p, 'endurance', 0)} CO:{getattr(p, 'control', 0)}"
            
        else:
            core = f"CH:{getattr(p, 'ch', 0)} PH:{getattr(p, 'ph', 0)} SP:{getattr(p, 'sp', 0)}"
        label = f"{p.first_name} {p.last_name} ({age}) - {role or p.primary_position} | {core}"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, p.player_id)
        return item
