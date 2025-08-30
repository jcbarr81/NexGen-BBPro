import os
import csv
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QTabWidget,
    QListWidget,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QComboBox,
    QMessageBox,
    QListWidgetItem,
    QGroupBox,
    QMenuBar,
)

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - fallback for environments without PyQt6
    class QApplication:  # type: ignore
        @staticmethod
        def quit():
            pass
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from ui.lineup_editor import LineupEditor
from ui.pitching_editor import PitchingEditor
from ui.position_players_dialog import PositionPlayersDialog
from ui.pitchers_window import PitchersWindow
from ui.transactions_window import TransactionsWindow
from ui.team_settings_dialog import TeamSettingsDialog
from ui.standings_window import StandingsWindow
from ui.schedule_window import ScheduleWindow
from ui.team_schedule_window import TeamScheduleWindow
from ui.trade_dialog import TradeDialog
from ui.team_stats_window import TeamStatsWindow
from ui.league_stats_window import LeagueStatsWindow
from ui.league_leaders_window import LeagueLeadersWindow
from utils.roster_loader import load_roster, save_roster
from utils.player_loader import load_players_from_csv
from utils.news_reader import read_latest_news
from utils.free_agent_finder import find_free_agents
from utils.team_loader import load_teams, save_team_settings
from utils.pitcher_role import get_role
from utils.trade_utils import get_pending_trades
from utils.path_utils import get_base_dir
from .theme import _toggle_theme


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Convert ``#RRGGBB`` or ``#RGB`` strings to an (r, g, b) tuple."""
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _contrast_text_color(hex_color: str) -> str:
    """Return black or white for legible text on ``hex_color`` backgrounds."""
    r, g, b = _hex_to_rgb(hex_color)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance > 180 else "#ffffff"


PREDEFINED_COLOR_SCHEMES: dict[str, tuple[str, str]] = {
    "Light": ("#f5f5f5", "#d0d0d0"),
    "Dark": ("#2e3440", "#4c566a"),
    "Classic": ("#003366", "#cccccc"),
}


class OwnerDashboard(QWidget):
    """Owner-facing dashboard showing roster and quick actions.

    Fixes:
    - Pitchers now display **AS/EN/CO** instead of CH/PH/SP.
    - Roster counts & validation are correct and the header updates live.
    - No broken method calls (e.g., update_roster_count_display).
    """

    def __init__(self, team_id: str):
        super().__init__()
        self.team_id = team_id
        self.unsaved_changes = False

        # Data
        self.players = {p.player_id: p for p in load_players_from_csv("data/players.csv")}
        self.roster = load_roster(team_id)
        teams = {t.team_id: t for t in load_teams()}
        self.team = teams.get(team_id)

        # Window
        # Open slightly larger for better visibility.
        self.setGeometry(150, 150, 1200, 850)
        self.setWindowTitle(f"Owner Dashboard - {team_id}")

        bold = QFont()
        bold.setBold(True)
        bold.setPointSize(10)

        main = QVBoxLayout()
        main.setContentsMargins(10, 10, 10, 10)

        # Menu bar
        menubar = QMenuBar()
        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)
        color_menu = file_menu.addMenu("Color Scheme")
        toggle_action = color_menu.addAction("Toggle Dark Mode")
        toggle_action.triggered.connect(_toggle_theme)
        for name, (primary, secondary) in PREDEFINED_COLOR_SCHEMES.items():
            action = color_menu.addAction(name)
            action.triggered.connect(
                lambda _=False, p=primary, s=secondary: self.apply_color_scheme(p, s)
            )
        team_colors_action = color_menu.addAction("Team Colors")
        team_colors_action.triggered.connect(self.apply_team_colors)
        team_menu = menubar.addMenu("Team")
        pos_action = team_menu.addAction("Position Players")
        pit_action = team_menu.addAction("Pitchers")
        lineups_action = team_menu.addAction("Lineups")
        pitch_staff_action = team_menu.addAction("Pitching Staff")
        trans_action = team_menu.addAction("Transactions")
        settings_action = team_menu.addAction("Settings")
        stats_action = team_menu.addAction("Stats")
        self.team_schedule_action = team_menu.addAction("Schedule")
        self.team_schedule_action.triggered.connect(self.open_team_schedule_window)
        pos_action.triggered.connect(self.open_position_players_dialog)
        pit_action.triggered.connect(self.open_pitchers_window)
        lineups_action.triggered.connect(self.open_lineup_editor)
        pitch_staff_action.triggered.connect(self.open_pitching_editor)
        trans_action.triggered.connect(self.open_transactions_page)
        settings_action.triggered.connect(self.open_team_settings)
        stats_action.triggered.connect(self.open_team_stats_window)
        league_menu = menubar.addMenu("League")
        self.standings_action = league_menu.addAction("Standings")
        self.schedule_action = league_menu.addAction("Schedule")
        self.league_stats_action = league_menu.addAction("Statistics")
        self.league_leaders_action = league_menu.addAction("Leaders")
        self.standings_action.triggered.connect(self.open_standings_window)
        self.schedule_action.triggered.connect(self.open_schedule_window)
        self.league_stats_action.triggered.connect(self.open_league_stats_window)
        self.league_leaders_action.triggered.connect(self.open_league_leaders_window)
        main.setMenuBar(menubar)

        logo_path = get_base_dir() / "logo" / "teams" / f"{team_id.lower()}.png"
        if logo_path.exists():
            logo_label = QLabel()
            pix = QPixmap(str(logo_path)).scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(pix)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main.addWidget(logo_label)

        welcome = QLabel(f"Welcome, Owner of {team_id}!")
        welcome.setFont(bold)
        main.addWidget(welcome)

        # News
        main.addWidget(QLabel("League News"))
        self.news_feed = QTextEdit()
        self.news_feed.setReadOnly(True)
        self.news_feed.setMinimumHeight(120)
        self.news_feed.setStyleSheet("background-color:#1e1e1e;color:#ffffff;")
        self.news_feed.setFont(QFont("Courier New", 9))
        main.addWidget(self.news_feed)

        # Roster count label
        self.roster_count_label = QLabel()
        self.roster_count_label.setFont(bold)
        main.addWidget(self.roster_count_label)

        # Roster tabs
        roster_box = QGroupBox("Roster")
        roster_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.act_list = self._build_roster_list(self.roster.act)
        self.aaa_list = self._build_roster_list(self.roster.aaa)
        self.low_list = self._build_roster_list(self.roster.low)
        self.tabs.addTab(self.act_list, "Active (ACT)")
        self.tabs.addTab(self.aaa_list, "AAA")
        self.tabs.addTab(self.low_list, "LOW")
        roster_layout.addWidget(self.tabs)
        roster_box.setLayout(roster_layout)
        main.addWidget(roster_box)

        # Move / Cut
        move_box = QGroupBox("Manage Players")
        move_layout = QHBoxLayout()
        self.move_dropdown = QComboBox()
        self.move_dropdown.addItems(["ACT", "AAA", "LOW"])
        self.move_button = QPushButton("Move Selected Player")
        self.cut_button = QPushButton("Cut Selected Player")
        self.move_button.clicked.connect(self.move_selected_player)
        self.cut_button.clicked.connect(self.cut_selected_player)
        move_layout.addWidget(QLabel("Move to:"))
        move_layout.addWidget(self.move_dropdown)
        move_layout.addWidget(self.move_button)
        move_layout.addWidget(self.cut_button)
        move_box.setLayout(move_layout)
        main.addWidget(move_box)

        # Free agents
        action_box = QGroupBox("Transactions")
        action_layout = QHBoxLayout()
        self.trade_button = QPushButton("Open Trade Center")
        self.sign_button = QPushButton("Sign Free Agent")
        self.trade_button.clicked.connect(self.open_trade_dialog)
        self.sign_button.clicked.connect(self.sign_free_agent)
        action_layout.addWidget(self.trade_button)
        action_layout.addWidget(self.sign_button)
        action_box.setLayout(action_layout)
        main.addWidget(action_box)

        # Lineup/Pitching staff management
        lineup_layout = QHBoxLayout()
        self.lineup_button = QPushButton("Manage Lineups")
        self.rotation_button = QPushButton("Manage Pitching Staff")
        self.lineup_button.setFont(bold)
        self.rotation_button.setFont(bold)
        self.lineup_button.setFixedSize(160, 30)
        self.rotation_button.setFixedSize(160, 30)
        self.lineup_button.clicked.connect(self.open_lineup_editor)
        self.rotation_button.clicked.connect(self.open_pitching_editor)
        lineup_layout.addWidget(self.lineup_button)
        lineup_layout.addWidget(self.rotation_button)
        main.addLayout(lineup_layout)

        self.setLayout(main)
        self.apply_team_colors()
        # Re-apply explicit style for the news feed to override theme background
        self.news_feed.setStyleSheet("background-color:#1e1e1e;color:#ffffff;")
        self.load_news_feed()
        self.update_roster_count_display()
        self.update_window_title()
        pending = get_pending_trades(self.team_id)
        if pending:
            QMessageBox.information(
                self,
                "Pending Trades",
                f"You have {len(pending)} pending trade(s). Open Trade Center to respond.",
            )

    def apply_team_colors(self):
        """Apply the team's color scheme to the dashboard."""
        if not self.team:
            return
        self.apply_color_scheme(self.team.primary_color, self.team.secondary_color)

    def apply_color_scheme(self, primary: str, secondary: str):
        """Apply a custom color scheme to the dashboard."""
        text_color = _contrast_text_color(primary)
        button_text = _contrast_text_color(secondary)
        self.setStyleSheet(
            f"""
            QWidget {{background-color: {primary}; color: {text_color};}}
            QPushButton {{background-color: {secondary}; color: {button_text};}}
            """
        )

    # ---------- UI helpers ----------
    def _build_roster_list(self, player_ids):
        lw = QListWidget()
        for pid in player_ids:
            p = self.players.get(pid)
            if not p:
                continue
            lw.addItem(self._make_player_item(p))
        return lw

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

    def refresh_roster_views(self):
        # Rebuild all three lists from current roster state
        self.act_list.clear()
        self.aaa_list.clear()
        self.low_list.clear()
        for pid in self.roster.act:
            if pid in self.players:
                self.act_list.addItem(self._make_player_item(self.players[pid]))
        for pid in self.roster.aaa:
            if pid in self.players:
                self.aaa_list.addItem(self._make_player_item(self.players[pid]))
        for pid in self.roster.low:
            if pid in self.players:
                self.low_list.addItem(self._make_player_item(self.players[pid]))

    # ---------- Buttons ----------
    def open_lineup_editor(self):
        LineupEditor(self.team_id).exec()

    def open_pitching_editor(self):
        PitchingEditor(self.team_id).exec()

    def open_position_players_dialog(self):
        PositionPlayersDialog(self.players, self.roster).exec()

    def open_pitchers_window(self):
        PitchersWindow(self.players, self.roster).exec()

    def open_transactions_page(self):
        TransactionsWindow().exec()

    def open_standings_window(self):
        """Open the league standings dialog."""
        StandingsWindow(self).exec()

    def open_schedule_window(self):
        """Open the league schedule dialog."""
        ScheduleWindow(self).exec()

    def open_team_schedule_window(self):
        """Open the current team's schedule dialog."""
        if not getattr(self, "team_id", None):
            QMessageBox.warning(self, "Error", "Team information not available.")
            return
        TeamScheduleWindow(self.team_id, self).exec()

    def open_team_stats_window(self):
        """Open the team statistics window."""
        TeamStatsWindow(self.team, self.players, self.roster, self).exec()

    def open_league_stats_window(self):
        """Open the league-wide statistics window."""
        teams = load_teams()
        LeagueStatsWindow(teams, self.players.values(), self).exec()

    def open_league_leaders_window(self):
        """Open the league leaders window."""
        LeagueLeadersWindow(self.players.values(), self).exec()

    def open_team_settings(self):
        if not self.team:
            QMessageBox.warning(self, "Error", "Team information not available.")
            return
        dialog = TeamSettingsDialog(self.team, self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.team.primary_color = settings["primary_color"]
            self.team.secondary_color = settings["secondary_color"]
            self.team.stadium = settings["stadium"]
            save_team_settings(self.team)
            self.apply_team_colors()
            # Preserve dark theme for news feed
            self.news_feed.setStyleSheet("background-color:#1e1e1e;color:#ffffff;")
            QMessageBox.information(self, "Saved", "Team settings updated.")

    def move_selected_player(self):
        current_tab = self.tabs.currentIndex()
        current_list = [self.act_list, self.aaa_list, self.low_list][current_tab]
        selected_item = current_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a player to move.")
            return
        player_id = selected_item.data(Qt.ItemDataRole.UserRole)
        target_level = self.move_dropdown.currentText().lower()
        from_level = ["act", "aaa", "low"][current_tab]
        if target_level == from_level:
            return
        # update model
        getattr(self.roster, from_level).remove(player_id)
        getattr(self.roster, target_level).append(player_id)
        self.refresh_roster_views()
        self.update_roster_count_display()
        self.unsaved_changes = True
        self.update_window_title()

    def cut_selected_player(self):
        current_tab = self.tabs.currentIndex()
        current_list = [self.act_list, self.aaa_list, self.low_list][current_tab]
        selected_item = current_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a player to cut.")
            return
        player_id = selected_item.data(Qt.ItemDataRole.UserRole)
        level = ["act", "aaa", "low"][current_tab]
        confirm = QMessageBox.question(
            self,
            "Confirm Cut",
            f"Are you sure you want to cut {player_id} from {level.upper()}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            getattr(self.roster, level).remove(player_id)
            self.refresh_roster_views()
            self.update_roster_count_display()
            self.unsaved_changes = True
            self.update_window_title()

    def save_roster(self):
        act_total = len(self.roster.act)
        aaa_total = len(self.roster.aaa)
        low_total = len(self.roster.low)
        # Count ACT position players (not pitchers)
        act_pos_players = 0
        for pid in self.roster.act:
            p = self.players.get(pid)
            if not p:
                continue
            if not get_role(p):
                act_pos_players += 1
        # Validations per spec
        if act_total > 25:
            QMessageBox.warning(self, "Validation Error", "Active roster cannot exceed 25 players.")
            return
        if act_pos_players < 11:
            QMessageBox.warning(self, "Validation Error", "Active roster must have at least 11 position players.")
            return
        if aaa_total > 15:
            QMessageBox.warning(self, "Validation Error", "AAA roster cannot exceed 15 players.")
            return
        if low_total > 10:
            QMessageBox.warning(self, "Validation Error", "LOW roster cannot exceed 10 players.")
            return
        try:
            save_roster(self.team_id, self.roster)
            self.unsaved_changes = False
            self.update_window_title()
            QMessageBox.information(self, "Success", "Roster saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save roster: {e}")

    def open_trade_dialog(self):
        TradeDialog(self.team_id, self).exec()

    def sign_free_agent(self):
        try:
            free_agents = find_free_agents(self.players, self.roster)
            if not free_agents:
                QMessageBox.information(self, "Free Agents", "No free agents available to sign.")
                return
            # For now, auto-sign the first free agent to ACT (can be replaced with a dialog)
            pid = free_agents[0]
            self.roster.act.append(pid)
            self.refresh_roster_views()
            self.update_roster_count_display()
            self.unsaved_changes = True
            QMessageBox.information(self, "Free Agents", f"Signed free agent: {pid}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to sign free agent: {e}")

    def load_news_feed(self):
        """Load the latest league news into the dashboard."""
        try:
            lines = read_latest_news(file_path="data/news_feed.txt")
            self.news_feed.setPlainText("".join(lines))
        except Exception as e:
            self.news_feed.setPlainText(f"(Failed to load news)\n{e}")

    def update_roster_count_display(self):
        act_total = len(self.roster.act)
        aaa_total = len(self.roster.aaa)
        low_total = len(self.roster.low)
        act_pos_players = sum(
            1 for pid in self.roster.act
            if pid in self.players and not get_role(self.players[pid])
        )
        self.roster_count_label.setText(
            f"Active: {act_total} (Pos: {act_pos_players})   |   AAA: {aaa_total}   |   LOW: {low_total}"
        )

    def calculate_age(self, birthdate_str: str):
        try:
            birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        except Exception:
            return "?"

    def update_window_title(self):
        title = f"Owner Dashboard - {self.team_id}"
        if self.unsaved_changes:
            title += " *"
        self.setWindowTitle(title)
