"""Admin dashboard window using modern navigation.

This module restructures the legacy admin dashboard to follow the layout
demonstrated in :mod:`ui_template`.  Navigation is handled through a sidebar
of :class:`NavButton` controls which swap pages in a :class:`QStackedWidget`.
Each page groups related actions inside a :class:`Card` with a small section
header provided by :func:`section_title`.

Only the user interface wiring has changed – the underlying callbacks are the
same routines that existed in the previous tab based implementation.  The goal
is to keep behaviour intact while presenting a cleaner API for future
expansion.
"""

from __future__ import annotations

import csv

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressDialog,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .components import Card, NavButton, section_title
from ui.window_utils import ensure_on_top, show_on_top
from .theme import _toggle_theme
from .team_entry_dialog import TeamEntryDialog
from .exhibition_game_dialog import ExhibitionGameDialog
from .playbalance_editor import PlayBalanceEditor
from .season_progress_window import SeasonProgressWindow
from .owner_dashboard import OwnerDashboard
from utils.trade_utils import load_trades, save_trade
from utils.news_logger import log_news_event
from utils.roster_loader import load_roster
from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.user_manager import add_user, load_users, update_user
from utils.path_utils import get_base_dir
from utils.pitcher_role import get_role
from utils.pitching_autofill import autofill_pitching_staff
from playbalance.league_creator import create_league


# ---------------------------------------------------------------------------
# Page widgets
# ---------------------------------------------------------------------------


class LeaguePage(QWidget):
    """Actions related to league-wide management."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("League Management"))

        self.review_button = QPushButton("Review Trades")
        card.layout().addWidget(self.review_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.create_league_button = QPushButton("Create League")
        card.layout().addWidget(
            self.create_league_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.exhibition_button = QPushButton("Simulate Exhibition Game")
        card.layout().addWidget(
            self.exhibition_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.playbalance_button = QPushButton("Edit Play Balance")
        card.layout().addWidget(
            self.playbalance_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.season_progress_button = QPushButton("Season Progress")
        card.layout().addWidget(
            self.season_progress_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()


class TeamsPage(QWidget):
    """Team management helpers."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("Team Management"))

        self.team_dashboard_button = QPushButton("Open Team Dashboard")
        card.layout().addWidget(
            self.team_dashboard_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.set_lineups_button = QPushButton("Set All Team Lineups")
        card.layout().addWidget(
            self.set_lineups_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.set_pitching_button = QPushButton("Set All Pitching Staff Roles")
        card.layout().addWidget(
            self.set_pitching_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.auto_reassign_button = QPushButton("Auto Reassign All Rosters")
        card.layout().addWidget(
            self.auto_reassign_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()


class UsersPage(QWidget):
    """User account management."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("User Management"))

        self.add_user_button = QPushButton("Add User")
        card.layout().addWidget(
            self.add_user_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.edit_user_button = QPushButton("Edit User")
        card.layout().addWidget(
            self.edit_user_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()


class UtilitiesPage(QWidget):
    """Miscellaneous utilities for data management."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("Utilities"))

        self.generate_logos_button = QPushButton("Generate Team Logos")
        card.layout().addWidget(
            self.generate_logos_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.generate_avatars_button = QPushButton("Generate Player Avatars")
        card.layout().addWidget(
            self.generate_avatars_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    """Administration console for commissioners."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Admin Dashboard")
        self.resize(1000, 700)

        self.team_dashboards: list[OwnerDashboard] = []

        # sidebar ---------------------------------------------------------
        sidebar = QWidget(objectName="Sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(10, 12, 10, 12)
        side.setSpacing(6)

        side.addWidget(QLabel("⚾  Commissioner"))

        self.btn_league = NavButton("  League")
        self.btn_teams = NavButton("  Teams")
        self.btn_users = NavButton("  Users")
        self.btn_utils = NavButton("  Utilities")
        for b in (self.btn_league, self.btn_teams, self.btn_users, self.btn_utils):
            side.addWidget(b)
        side.addStretch()

        self.nav_buttons = {
            "league": self.btn_league,
            "teams": self.btn_teams,
            "users": self.btn_users,
            "utils": self.btn_utils,
        }

        # header + stacked pages -----------------------------------------
        header = QWidget(objectName="Header")
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 10, 18, 10)
        h.addWidget(QLabel("Admin Dashboard", objectName="Title"))
        h.addStretch()

        self.stack = QStackedWidget()
        self.pages = {
            "league": LeaguePage(),
            "teams": TeamsPage(),
            "users": UsersPage(),
            "utils": UtilitiesPage(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        rv.addWidget(header)
        rv.addWidget(self.stack)

        # root layout -----------------------------------------------------
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(sidebar)
        root.addWidget(right)
        root.setStretchFactor(right, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        # menu ------------------------------------------------------------
        self._build_menu()

        # signals ---------------------------------------------------------
        self.btn_league.clicked.connect(lambda: self._go("league"))
        self.btn_teams.clicked.connect(lambda: self._go("teams"))
        self.btn_users.clicked.connect(lambda: self._go("users"))
        self.btn_utils.clicked.connect(lambda: self._go("utils"))

        # connect page buttons to actions
        lp: LeaguePage = self.pages["league"]
        lp.review_button.clicked.connect(self.open_trade_review)
        lp.create_league_button.clicked.connect(self.open_create_league)
        lp.exhibition_button.clicked.connect(self.open_exhibition_dialog)
        lp.playbalance_button.clicked.connect(self.open_playbalance_editor)
        lp.season_progress_button.clicked.connect(self.open_season_progress)

        tp: TeamsPage = self.pages["teams"]
        tp.team_dashboard_button.clicked.connect(self.open_team_dashboard)
        tp.set_lineups_button.clicked.connect(self.set_all_lineups)
        tp.set_pitching_button.clicked.connect(self.set_all_pitching_roles)
        tp.auto_reassign_button.clicked.connect(self.auto_reassign_rosters)

        up: UsersPage = self.pages["users"]
        up.add_user_button.clicked.connect(self.open_add_user)
        up.edit_user_button.clicked.connect(self.open_edit_user)

        util: UtilitiesPage = self.pages["utils"]
        util.generate_logos_button.clicked.connect(self.generate_team_logos)
        util.generate_avatars_button.clicked.connect(self.generate_player_avatars)

        # default page
        self.btn_league.setChecked(True)
        self._go("league")

    # ------------------------------------------------------------------
    # Menu and navigation helpers
    # ------------------------------------------------------------------

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
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        btn = self.nav_buttons.get(key)
        if btn:
            btn.setChecked(True)
        idx = list(self.pages.keys()).index(key)
        self.stack.setCurrentIndex(idx)
        self.statusBar().showMessage(f"Ready • {key.capitalize()}")


    # ------------------------------------------------------------------
    # Existing behaviours
    # ------------------------------------------------------------------

    # The methods below are largely unchanged from the original
    # implementation.  They provide the actual behaviour for the various
    # buttons defined on the dashboard pages.

    def open_trade_review(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Review Pending Trades")
        dialog.setMinimumSize(600, 400)

        trades = load_trades()
        players = {p.player_id: p for p in load_players_from_csv("data/players.csv")}
        teams = {t.team_id: t for t in load_teams("data/teams.csv")}

        layout = QVBoxLayout()

        trade_list = QListWidget()
        trade_map = {}

        for t in trades:
            if t.status != "pending":
                continue
            give_names = [
                f"{pid} ({players[pid].first_name} {players[pid].last_name})"
                for pid in t.give_player_ids
                if pid in players
            ]
            recv_names = [
                f"{pid} ({players[pid].first_name} {players[pid].last_name})"
                for pid in t.receive_player_ids
                if pid in players
            ]
            summary = (
                f"{t.trade_id}: {t.from_team} → {t.to_team} | "
                f"Give: {', '.join(give_names)} | Get: {', '.join(recv_names)}"
            )
            trade_list.addItem(summary)
            trade_map[summary] = t

        def process_trade(accept: bool = True) -> None:
            selected = trade_list.currentItem()
            if not selected:
                return
            summary = selected.text()
            trade = trade_map[summary]

            from_roster = load_roster(trade.from_team)
            to_roster = load_roster(trade.to_team)

            for pid in trade.give_player_ids:
                for level in ["act", "aaa", "low"]:
                    lst = getattr(from_roster, level)
                    if pid in lst:
                        lst.remove(pid)
                        getattr(to_roster, level).append(pid)
                        break

            for pid in trade.receive_player_ids:
                for level in ["act", "aaa", "low"]:
                    lst = getattr(to_roster, level)
                    if pid in lst:
                        lst.remove(pid)
                        getattr(from_roster, level).append(pid)
                        break

            def save_roster(roster):
                path = get_base_dir() / "data" / "rosters" / f"{roster.team_id}.csv"
                with path.open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["player_id", "level"])
                    writer.writeheader()
                    for lvl in ["act", "aaa", "low"]:
                        for pid in getattr(roster, lvl):
                            writer.writerow({"player_id": pid, "level": lvl.upper()})

            save_roster(from_roster)
            save_roster(to_roster)

            trade.status = "accepted" if accept else "rejected"
            save_trade(trade)

            log_news_event(
                f"TRADE {'ACCEPTED' if accept else 'REJECTED'}: {summary}"
            )
            QMessageBox.information(
                dialog, "Trade Processed", f"{summary} marked as {trade.status.upper()}."
            )
            trade_list.takeItem(trade_list.currentRow())

        btn_layout = QHBoxLayout()
        accept_btn = QPushButton("Accept Trade")
        reject_btn = QPushButton("Reject Trade")
        accept_btn.clicked.connect(lambda: process_trade(True))
        reject_btn.clicked.connect(lambda: process_trade(False))
        btn_layout.addWidget(accept_btn)
        btn_layout.addWidget(reject_btn)

        layout.addWidget(trade_list)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        show_on_top(dialog)

    def generate_team_logos(self) -> None:
        teams = load_teams("data/teams.csv")
        progress = QProgressDialog(
            "Generating team logos...",
            None,
            0,
            len(teams),
            self,
        )
        progress.setWindowTitle("Generating Logos")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        def cb(done: int, total: int) -> None:
            progress.setValue(done)
            QApplication.processEvents()

        try:
            from utils.logo_generator import generate_team_logos

            out_dir = generate_team_logos(progress_callback=cb)
            QMessageBox.information(
                self, "Logos Generated", f"Team logos saved to {out_dir}"
            )
        except Exception as exc:  # pragma: no cover - dialog handling
            QMessageBox.warning(self, "Error", str(exc))

    def generate_player_avatars(self) -> None:
        initial = (
            QMessageBox.question(
                self,
                "Initial Creation",
                "Is this the initial creation of player avatars?\n"
                "Yes will remove existing avatars (except Template).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

        progress = QProgressDialog(
            "Generating player avatars...",
            None,
            0,
            100,
            self,
        )
        progress.setWindowTitle("Generating Avatars")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        try:
            from utils.avatar_generator import generate_player_avatars

            out_dir = generate_player_avatars(
                progress_callback=progress.setValue, initial_creation=initial
            )
            QMessageBox.information(
                self, "Avatars Generated", f"Player avatars saved to {out_dir}"
            )
        except Exception as exc:  # pragma: no cover - dialog handling
            QMessageBox.warning(self, "Error", str(exc))

    def open_add_user(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add User")

        layout = QVBoxLayout()

        username_input = QLineEdit()
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        team_combo = QComboBox()

        layout.addWidget(QLabel("Username:"))
        layout.addWidget(username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(password_input)
        layout.addWidget(QLabel("Team:"))
        layout.addWidget(team_combo)

        data_dir = get_base_dir() / "data"
        teams = load_teams(data_dir / "teams.csv")
        team_combo.addItem("None", "")
        for t in teams:
            team_combo.addItem(f"{t.name} ({t.team_id})", userData=t.team_id)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def handle_add() -> None:
            username = username_input.text().strip()
            password = password_input.text().strip()
            team_id = team_combo.currentData()
            if not username or not password:
                QMessageBox.warning(dialog, "Error", "Username and password required")
                return
            try:
                role = "owner" if team_id else "admin"
                add_user(username, password, role, team_id, data_dir / "users.txt")
            except ValueError as e:
                QMessageBox.warning(dialog, "Error", str(e))
                return
            QMessageBox.information(dialog, "Success", f"User {username} added.")
            dialog.accept()

        add_btn.clicked.connect(handle_add)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.setLayout(layout)
        show_on_top(dialog)

    def open_edit_user(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit User")

        data_dir = get_base_dir() / "data"
        users = load_users(data_dir / "users.txt")
        if not users:
            QMessageBox.information(self, "No Users", "No users available.")
            return

        layout = QVBoxLayout()

        user_combo = QComboBox()
        for u in users:
            user_combo.addItem(u["username"], userData=u)

        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)

        team_combo = QComboBox()
        teams = load_teams(data_dir / "teams.csv")
        team_combo.addItem("None", "")
        for t in teams:
            team_combo.addItem(f"{t.name} ({t.team_id})", userData=t.team_id)

        layout.addWidget(QLabel("User:"))
        layout.addWidget(user_combo)
        layout.addWidget(QLabel("New Password:"))
        layout.addWidget(password_input)
        layout.addWidget(QLabel("Team:"))
        layout.addWidget(team_combo)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Update")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def sync_fields() -> None:
            user = user_combo.currentData()
            index = team_combo.findData(user["team_id"])
            if index >= 0:
                team_combo.setCurrentIndex(index)
            password_input.clear()

        user_combo.currentIndexChanged.connect(lambda _: sync_fields())
        sync_fields()

        def handle_update() -> None:
            user = user_combo.currentData()
            new_password = password_input.text().strip() or None
            new_team = team_combo.currentData()
            try:
                update_user(
                    user["username"],
                    new_password,
                    new_team,
                    data_dir / "users.txt",
                )
            except ValueError as e:
                QMessageBox.warning(dialog, "Error", str(e))
                return
            QMessageBox.information(
                dialog, "Success", f"User {user['username']} updated."
            )
            dialog.accept()

        save_btn.clicked.connect(handle_update)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.setLayout(layout)
        show_on_top(dialog)

    def open_team_dashboard(self) -> None:
        teams = load_teams(get_base_dir() / "data" / "teams.csv")
        team_ids = [t.team_id for t in teams]
        if not team_ids:
            QMessageBox.information(self, "No Teams", "No teams available.")
            return
        team_id, ok = QInputDialog.getItem(
            self, "Open Team Dashboard", "Select a team:", team_ids, 0, False
        )
        if ok and team_id:
            dashboard = OwnerDashboard(team_id)
            show_on_top(dashboard)
            self.team_dashboards.append(dashboard)

    def set_all_lineups(self) -> None:
        data_dir = get_base_dir() / "data"
        players_file = data_dir / "players.csv"
        if not players_file.exists():
            QMessageBox.warning(self, "Error", "Players file not found.")
            return
        players = {}
        with players_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("player_id", "").strip()
                players[pid] = {
                    "primary": row.get("primary_position", "").strip(),
                    "others": row.get("other_positions", "").split("|")
                    if row.get("other_positions")
                    else [],
                    "is_pitcher": row.get("is_pitcher") == "1",
                }

        teams = load_teams(data_dir / "teams.csv")
        for team in teams:
            try:
                roster = load_roster(team.team_id)
            except FileNotFoundError:
                continue
            act_ids = roster.act
            lineup: list[tuple[str, str]] = []
            used = set()
            for pos in ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]:
                for pid in players:
                    if pid not in act_ids or pid in used:
                        continue
                    pdata = players[pid]
                    if pos == "DH":
                        if pdata["is_pitcher"]:
                            continue
                    else:
                        if pos != pdata["primary"] and pos not in pdata["others"]:
                            continue
                    lineup.append((pid, pos))
                    used.add(pid)
                    break
            lineup_dir = data_dir / "lineups"
            lineup_dir.mkdir(parents=True, exist_ok=True)
            for vs in ("vs_lhp", "vs_rhp"):
                path = lineup_dir / f"{team.team_id}_{vs}.csv"
                with path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["order", "player_id", "position"])
                    for i, (pid, pos) in enumerate(lineup, start=1):
                        writer.writerow([i, pid, pos])
        QMessageBox.information(self, "Lineups Set", "Lineups auto-filled for all teams.")

    def set_all_pitching_roles(self) -> None:
        data_dir = get_base_dir() / "data"
        players_file = data_dir / "players.csv"
        if not players_file.exists():
            QMessageBox.warning(self, "Error", "Players file not found.")
            return
        players = {}
        with players_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("player_id", "").strip()
                players[pid] = {
                    "primary_position": row.get("primary_position", "").strip(),
                    "role": row.get("role", "").strip(),
                    "endurance": row.get("endurance", ""),
                }

        teams = load_teams(data_dir / "teams.csv")
        for team in teams:
            try:
                roster = load_roster(team.team_id)
            except FileNotFoundError:
                continue
            available = [
                (pid, players[pid])
                for pid in roster.act
                if pid in players and get_role(players[pid])
            ]
            assignments = autofill_pitching_staff(available)
            path = data_dir / "rosters" / f"{team.team_id}_pitching.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for role, pid in assignments.items():
                    writer.writerow([pid, role])
        QMessageBox.information(
            self, "Pitching Staff Set", "Pitching roles auto-filled for all teams."
        )

    def auto_reassign_rosters(self) -> None:
        """Automatically reassign players across roster levels for all teams.

        Policies:
        - Active roster: max 25 players and at least 11 position players
        - AAA roster: max 15 players
        - Low roster: max 10 players
        Injured players remain on DL/IR and are not considered for promotion.
        """
        try:
            from services.roster_auto_assign import auto_assign_all_teams

            auto_assign_all_teams()
            QMessageBox.information(
                self, "Rosters Updated", "Auto reassigned rosters for all teams."
            )
        except Exception as exc:  # pragma: no cover - UI feedback only
            QMessageBox.warning(self, "Auto Reassign Failed", str(exc))

    def open_create_league(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Overwrite Existing League?",
            (
                "Creating a new league will overwrite the current league and"
                " teams. Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        league_name, ok = QInputDialog.getText(
            self, "League Name", "Enter league name:"
        )
        if not ok or not league_name:
            return
        league_name = league_name.strip()

        div_text, ok = QInputDialog.getText(
            self, "Divisions", "Enter division names separated by commas:"
        )
        if not ok or not div_text:
            return
        divisions = [d.strip() for d in div_text.split(",") if d.strip()]
        if not divisions:
            return

        teams_per_div, ok = QInputDialog.getInt(
            self, "Teams", "Teams per division:", 2, 1, 20
        )
        if not ok:
            return

        dialog = TeamEntryDialog(divisions, teams_per_div, self)
        ensure_on_top(dialog)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        structure = dialog.get_structure()
        data_dir = get_base_dir() / "data"
        try:
            create_league(str(data_dir), structure, league_name)
        except OSError as e:  # pragma: no cover - destructive operation
            QMessageBox.critical(self, "Error", f"Failed to purge existing league: {e}")
            return
        QMessageBox.information(self, "League Created", "New league generated.")

    def open_exhibition_dialog(self) -> None:
        dlg = ExhibitionGameDialog(self)
        dlg.exec()

    def open_playbalance_editor(self) -> None:
        editor = PlayBalanceEditor(self)
        editor.exec()

    def open_season_progress(self) -> None:
        win = SeasonProgressWindow(self)
        win.show()


__all__ = [
    "MainWindow",
    "LeaguePage",
    "TeamsPage",
    "UsersPage",
    "UtilitiesPage",
]

