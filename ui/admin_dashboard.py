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
from PyQt6.QtGui import QAction, QIcon
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
    QTableWidget,
    QTableWidgetItem,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .components import Card, NavButton, section_title
from .admin_home_page import AdminHomePage
from ui.window_utils import ensure_on_top, show_on_top
from .theme import _toggle_theme
from .team_entry_dialog import TeamEntryDialog
from .exhibition_game_dialog import ExhibitionGameDialog
from .playbalance_editor import PlayBalanceEditor
from playbalance.draft_config import load_draft_config, save_draft_config
from .season_progress_window import SeasonProgressWindow
from .playoffs_window import PlayoffsWindow
from .free_agency_window import FreeAgencyWindow
from .news_window import NewsWindow
from .owner_dashboard import OwnerDashboard
from utils.trade_utils import load_trades, save_trade
from utils.news_logger import log_news_event
from utils.roster_loader import load_roster
from utils.lineup_autofill import auto_fill_lineup_for_team
from services.transaction_log import record_transaction
from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.user_manager import add_user, load_users, update_user
from utils.path_utils import get_base_dir
from utils.sim_date import get_current_sim_date
from utils.pitcher_role import get_role
from utils.pitching_autofill import autofill_pitching_staff
from playbalance.league_creator import create_league
from utils.roster_validation import missing_positions


# ---------------------------------------------------------------------------
# Page widgets
# ---------------------------------------------------------------------------


class LeaguePage(QWidget):
    """Actions related to league-wide management, grouped by intent."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        # Season Control --------------------------------------------------
        control = Card()
        control.layout().addWidget(section_title("Season Control"))

        self.season_progress_button = QPushButton("Season Progress")
        self.season_progress_button.setToolTip("Open the season progress window")
        control.layout().addWidget(self.season_progress_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.reset_opening_day_button = QPushButton("Reset to Opening Day")
        self.reset_opening_day_button.setObjectName("Danger")  # styled later
        self.reset_opening_day_button.setToolTip("Clear results/standings and rewind season to Opening Day")
        control.layout().addWidget(self.reset_opening_day_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.exhibition_button = QPushButton("Simulate Exhibition Game")
        self.exhibition_button.setToolTip("Run a quick exhibition between two teams")
        control.layout().addWidget(self.exhibition_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.playoffs_view_button = QPushButton("Open Playoffs Viewer")
        self.playoffs_view_button.setToolTip("View current playoff bracket and results")
        control.layout().addWidget(self.playoffs_view_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        control.layout().addStretch()

        # Operations ------------------------------------------------------
        ops = Card()
        ops.layout().addWidget(section_title("Operations"))

        self.review_button = QPushButton("Review Trades")
        self.review_button.setToolTip("Approve or reject pending trades")
        ops.layout().addWidget(self.review_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.create_league_button = QPushButton("Create League")
        self.create_league_button.setToolTip("Generate a new league structure (destructive)")
        ops.layout().addWidget(self.create_league_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.playbalance_button = QPushButton("Edit Play Balance")
        self.playbalance_button.setToolTip("Tune game balance parameters")
        ops.layout().addWidget(self.playbalance_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.free_agency_hub_button = QPushButton("Open Free Agency Hub")
        self.free_agency_hub_button.setToolTip("Browse unsigned players and simulate AI bids")
        ops.layout().addWidget(self.free_agency_hub_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.injury_center_button = QPushButton("Open Injury Center")
        self.injury_center_button.setToolTip("View league-wide injuries (read-only)")
        ops.layout().addWidget(self.injury_center_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        ops.layout().addStretch()

        layout.addWidget(control)
        layout.addWidget(ops)
        layout.addStretch()


class TeamsPage(QWidget):
    """Team management helpers, grouped for access and bulk actions."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        # Team Access -----------------------------------------------------
        access = Card()
        access.layout().addWidget(section_title("Team Access"))
        self.team_select = QComboBox()
        try:
            teams = load_teams("data/teams.csv")
            self.team_select.addItems([t.team_id for t in teams])
        except Exception:
            pass
        self.team_select.setEditable(True)
        self.team_select.setToolTip("Type to search by team id; used by 'Open Team Dashboard'")
        access.layout().addWidget(self.team_select)

        self.team_dashboard_button = QPushButton("Open Team Dashboard")
        self.team_dashboard_button.setToolTip("Open selected team's Owner Dashboard")
        access.layout().addWidget(self.team_dashboard_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        access.layout().addStretch()

        # Bulk Actions ----------------------------------------------------
        bulk = Card()
        bulk.layout().addWidget(section_title("Bulk Actions"))

        self.set_lineups_button = QPushButton("Set All Team Lineups")
        self.set_lineups_button.setToolTip("Auto-fill batting orders for all teams")
        bulk.layout().addWidget(self.set_lineups_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.set_pitching_button = QPushButton("Set All Pitching Staff Roles")
        self.set_pitching_button.setToolTip("Auto-assign pitching roles for all teams")
        bulk.layout().addWidget(self.set_pitching_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.auto_reassign_button = QPushButton("Auto Reassign All Rosters")
        self.auto_reassign_button.setToolTip("Reassign players across roster levels using policy constraints")
        bulk.layout().addWidget(self.auto_reassign_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Pre-flight note
        note = QLabel(
            "Actions affect all teams. Constraints: Active ≤ 25; AAA ≤ 15; Low ≤ 10."
        )
        note.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        bulk.layout().addWidget(note)
        bulk.layout().addStretch()

        layout.addWidget(access)
        layout.addWidget(bulk)
        layout.addStretch()


class UsersPage(QWidget):
    """User account management with search and list."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        card = Card()
        card.layout().addWidget(section_title("User Management"))

        # Search + users table
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by username or team id…")
        card.layout().addWidget(self.search)

        self.user_table = QTableWidget(0, 3)
        self.user_table.setHorizontalHeaderLabels(["Username", "Role", "Team"])
        self.user_table.setSortingEnabled(True)
        card.layout().addWidget(self.user_table)

        # Action row
        row = QHBoxLayout()
        self.add_user_button = QPushButton("Add User")
        self.edit_user_button = QPushButton("Edit User")
        row.addWidget(self.add_user_button)
        row.addWidget(self.edit_user_button)
        card.layout().addLayout(row)

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()

        # State
        self.selected_username: str | None = None
        self.search.textChanged.connect(self._populate)
        self.user_table.itemSelectionChanged.connect(self._capture_selection)
        self._populate()

    def refresh(self) -> None:
        """Public hook to repopulate the users table (used by Admin window)."""
        self._populate()

    def _capture_selection(self) -> None:
        items = self.user_table.selectedItems()
        self.selected_username = items[0].text() if items else None

    def _populate(self) -> None:
        from utils.user_manager import load_users
        needle = self.search.text().strip().lower()
        users = []
        try:
            users = load_users()
        except Exception:
            users = []
        rows = []
        for u in users:
            if not needle or needle in u["username"].lower() or needle in (u.get("team_id", "").lower()):
                rows.append((u["username"], u.get("role", ""), u.get("team_id", "")))
        self.user_table.setRowCount(len(rows))
        for r, (username, role, team) in enumerate(rows):
            self.user_table.setItem(r, 0, QTableWidgetItem(username))
            self.user_table.setItem(r, 1, QTableWidgetItem(role))
            self.user_table.setItem(r, 2, QTableWidgetItem(team))


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

        self.btn_dashboard = NavButton("  Dashboard")
        self.btn_league = NavButton("  League")
        self.btn_teams = NavButton("  Teams")
        self.btn_users = NavButton("  Users")
        self.btn_utils = NavButton("  Utilities")
        self.btn_draft = NavButton("  Draft")
        for b in (self.btn_dashboard, self.btn_league, self.btn_teams, self.btn_users, self.btn_utils, self.btn_draft):
            side.addWidget(b)
        side.addStretch()

        self.nav_buttons = {
            "dashboard": self.btn_dashboard,
            "league": self.btn_league,
            "teams": self.btn_teams,
            "users": self.btn_users,
            "utils": self.btn_utils,
            "draft": self.btn_draft,
        }
        # Nav icons and tooltips
        try:
            from pathlib import Path
            icon_dir = Path(__file__).resolve().parent / "icons"
            def _set(btn, name: str, tip: str) -> None:
                try:
                    btn.setIcon(QIcon(str(icon_dir / name)))
                    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                except Exception:
                    pass
                btn.setToolTip(tip)
            _set(self.btn_dashboard, "team_dashboard.svg", "League overview and quick actions")
            _set(self.btn_league, "season_progress.svg", "Season control and operations")
            _set(self.btn_teams, "team_dashboard.svg", "Open team dashboards and bulk actions")
            _set(self.btn_users, "edit_user.svg", "Manage accounts and roles")
            _set(self.btn_utils, "generate_logos.svg", "Logos/avatars and data tools")
            _set(self.btn_draft, "play_balance.svg", "Amateur Draft console and settings")
        except Exception:
            pass

        # header + stacked pages -----------------------------------------
        header = QWidget(objectName="Header")
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 10, 18, 10)
        h.addWidget(QLabel("Admin Dashboard", objectName="Title"))
        h.addStretch()

        self.stack = QStackedWidget()
        # Draft page
        class DraftPage(QWidget):
            def __init__(self):
                super().__init__()
                layout = QVBoxLayout(self)
                layout.setContentsMargins(18, 18, 18, 18)
                card = Card()
                card.layout().addWidget(section_title("Amateur Draft"))
                # Status label to explain availability
                self.draft_status_label = QLabel("")
                self.draft_status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                card.layout().addWidget(self.draft_status_label)
                self.view_draft_pool_button = QPushButton("View Draft Pool")
                self.view_draft_pool_button.setToolTip("Browse the draft pool once Draft Day arrives.")
                card.layout().addWidget(self.view_draft_pool_button, alignment=Qt.AlignmentFlag.AlignHCenter)
                self.start_resume_draft_button = QPushButton("Start/Resume Draft")
                self.start_resume_draft_button.setToolTip("Open the Draft Console on or after Draft Day.")
                card.layout().addWidget(self.start_resume_draft_button, alignment=Qt.AlignmentFlag.AlignHCenter)
                self.view_results_button = QPushButton("View Draft Results")
                self.view_results_button.setToolTip("Open results for the current season (after completion).")
                card.layout().addWidget(self.view_results_button, alignment=Qt.AlignmentFlag.AlignHCenter)
                self.draft_settings_button = QPushButton("Draft Settings")
                self.draft_settings_button.setToolTip("Configure rounds, pool size, and RNG seed (always available).")
                card.layout().addWidget(self.draft_settings_button, alignment=Qt.AlignmentFlag.AlignHCenter)
                card.layout().addStretch()
                layout.addWidget(card)
                layout.addStretch()
        self.pages = {
            "dashboard": AdminHomePage(self),
            "league": LeaguePage(),
            "teams": TeamsPage(),
            "users": UsersPage(),
            "utils": UtilitiesPage(),
            "draft": DraftPage(),
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
        self.btn_dashboard.clicked.connect(lambda: self._go("dashboard"))
        self.btn_league.clicked.connect(lambda: self._go("league"))
        self.btn_teams.clicked.connect(lambda: self._go("teams"))
        self.btn_users.clicked.connect(lambda: self._go("users"))
        self.btn_utils.clicked.connect(lambda: self._go("utils"))
        self.btn_draft.clicked.connect(lambda: self._go("draft"))

        # connect page buttons to actions
        lp: LeaguePage = self.pages["league"]
        lp.review_button.clicked.connect(self.open_trade_review)
        lp.create_league_button.clicked.connect(self.open_create_league)
        lp.exhibition_button.clicked.connect(self.open_exhibition_dialog)
        lp.playbalance_button.clicked.connect(self.open_playbalance_editor)
        lp.injury_center_button.clicked.connect(self.open_injury_center)
        lp.free_agency_hub_button.clicked.connect(self.open_free_agency)
        lp.season_progress_button.clicked.connect(self.open_season_progress)
        lp.playoffs_view_button.clicked.connect(self.open_playoffs_window)
        lp.reset_opening_day_button.clicked.connect(self.reset_to_opening_day)
        dp = self.pages["draft"]
        dp.view_draft_pool_button.clicked.connect(self.open_draft_pool)
        dp.start_resume_draft_button.clicked.connect(self.open_draft_console)
        dp.view_results_button.clicked.connect(self.open_draft_results)
        dp.draft_settings_button.clicked.connect(self.open_draft_settings)

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
        self.btn_dashboard.setChecked(True)
        self._go("dashboard")

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
        news_action = QAction("News Feed", self)
        news_action.triggered.connect(self.open_news_window)
        view_menu.addAction(news_action)

    def _status_with_date(self, base: str) -> str:
        date_str = get_current_sim_date()
        if date_str:
            return f"{base} | Date: {date_str}"
        return base

    def _go(self, key: str) -> None:
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        btn = self.nav_buttons.get(key)
        if btn:
            btn.setChecked(True)
        idx = list(self.pages.keys()).index(key)
        self.stack.setCurrentIndex(idx)
        self.statusBar().showMessage(self._status_with_date(f"Ready - {key.capitalize()}"))
        # Page-specific refresh hooks
        try:
            page = self.pages.get(key)
            if page is not None and hasattr(page, "refresh"):
                page.refresh()  # type: ignore[attr-defined]
        except Exception:
            pass
        if key == "draft":
            self._refresh_draft_page()

    # ------------------------------------------------------------------
    # Dashboard metrics helper
    # ------------------------------------------------------------------
    def get_admin_metrics(self) -> dict:
        """Return a small set of overview metrics for the Admin home page."""
        # Counts
        try:
            # Match the team list shown in the Standings window, which relies
            # on load_teams(data/teams.csv).
            teams = load_teams("data/teams.csv")
            team_count = len(teams)
        except Exception:
            team_count = 0
        try:
            players = load_players_from_csv("data/players.csv")
            player_count = len(players)
        except Exception:
            player_count = 0
        # Pending trades
        try:
            pending = sum(1 for t in load_trades() if getattr(t, "status", "") == "pending")
        except Exception:
            pending = 0
        # Season phase (best-effort)
        try:
            from playbalance.season_manager import SeasonManager
            phase = str(SeasonManager().phase.name)
        except Exception:
            phase = "Unknown"
        # Draft day and status
        try:
            available, cur_date, draft_date, completed = self._draft_availability_details()
            status = "Completed" if completed else ("Ready" if available else "Not yet")
        except Exception:
            draft_date, status = None, None
        return {
            "teams": team_count,
            "players": player_count,
            "pending_trades": pending,
            "season_phase": phase,
            "draft_day": draft_date,
            "draft_status": status,
        }


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

            outgoing_from: list[tuple[str, str]] = []
            incoming_to: list[tuple[str, str]] = []
            outgoing_to: list[tuple[str, str]] = []
            incoming_from: list[tuple[str, str]] = []

            if accept:
                from_roster = load_roster(trade.from_team)
                to_roster = load_roster(trade.to_team)

                for pid in trade.give_player_ids:
                    for level in ("act", "aaa", "low"):
                        lst = getattr(from_roster, level)
                        if pid in lst:
                            lst.remove(pid)
                            getattr(to_roster, level).append(pid)
                            outgoing_from.append((pid, level))
                            incoming_to.append((pid, level))
                            break

                for pid in trade.receive_player_ids:
                    for level in ("act", "aaa", "low"):
                        lst = getattr(to_roster, level)
                        if pid in lst:
                            lst.remove(pid)
                            getattr(from_roster, level).append(pid)
                            outgoing_to.append((pid, level))
                            incoming_from.append((pid, level))
                            break

                def save_roster(roster):
                    path = get_base_dir() / "data" / "rosters" / f"{roster.team_id}.csv"
                    with path.open("w", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=["player_id", "level"])
                        writer.writeheader()
                        for lvl in ("act", "aaa", "low"):
                            for pid in getattr(roster, lvl):
                                writer.writerow({"player_id": pid, "level": lvl.upper()})

                save_roster(from_roster)
                save_roster(to_roster)

            trade.status = "accepted" if accept else "rejected"
            save_trade(trade)

            if accept:
                try:
                    for pid, level in outgoing_from:
                        record_transaction(
                            action="trade_out",
                            team_id=trade.from_team,
                            player_id=pid,
                            from_level=level.upper(),
                            to_level=level.upper(),
                            counterparty=trade.to_team,
                            details=f"Trade {trade.trade_id} sent to {trade.to_team}",
                        )
                        record_transaction(
                            action="trade_in",
                            team_id=trade.to_team,
                            player_id=pid,
                            from_level=level.upper(),
                            to_level=level.upper(),
                            counterparty=trade.from_team,
                            details=f"Trade {trade.trade_id} acquired from {trade.from_team}",
                        )
                    for pid, level in outgoing_to:
                        record_transaction(
                            action="trade_out",
                            team_id=trade.to_team,
                            player_id=pid,
                            from_level=level.upper(),
                            to_level=level.upper(),
                            counterparty=trade.from_team,
                            details=f"Trade {trade.trade_id} sent to {trade.from_team}",
                        )
                        record_transaction(
                            action="trade_in",
                            team_id=trade.from_team,
                            player_id=pid,
                            from_level=level.upper(),
                            to_level=level.upper(),
                            counterparty=trade.to_team,
                            details=f"Trade {trade.trade_id} acquired from {trade.to_team}",
                        )
                except Exception:
                    pass

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
        role_combo = QComboBox()
        role_combo.addItem("Admin", userData="admin")
        role_combo.addItem("Owner", userData="owner")
        team_combo = QComboBox()

        layout.addWidget(QLabel("Username:"))
        layout.addWidget(username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(password_input)
        layout.addWidget(QLabel("Role:"))
        layout.addWidget(role_combo)
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
            role = role_combo.currentData()
            if not username or not password:
                QMessageBox.warning(dialog, "Error", "Username and password required")
                return
            try:
                # If owner role selected, require team assignment
                if role == "owner" and not team_id:
                    QMessageBox.warning(dialog, "Error", "Select a team for the owner role")
                    return
                add_user(username, password, role, team_id, data_dir / "users.txt")
            except ValueError as e:
                QMessageBox.warning(dialog, "Error", str(e))
                return
            QMessageBox.information(dialog, "Success", f"User {username} added.")
            dialog.accept()
            # Refresh Users page table if present
            try:
                up = self.pages.get("users")
                if up is not None and hasattr(up, "refresh"):
                    up.refresh()  # type: ignore[attr-defined]
            except Exception:
                pass

        def sync_team_enabled() -> None:
            enabled = (role_combo.currentData() == "owner")
            try:
                team_combo.setEnabled(enabled)
            except Exception:
                pass
        role_combo.currentIndexChanged.connect(lambda *_: sync_team_enabled())
        sync_team_enabled()

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
        role_combo = QComboBox()
        role_combo.addItem("Admin", userData="admin")
        role_combo.addItem("Owner", userData="owner")
        teams = load_teams(data_dir / "teams.csv")
        team_combo.addItem("None", "")
        for t in teams:
            team_combo.addItem(f"{t.name} ({t.team_id})", userData=t.team_id)

        layout.addWidget(QLabel("User:"))
        layout.addWidget(user_combo)
        layout.addWidget(QLabel("New Password:"))
        layout.addWidget(password_input)
        layout.addWidget(QLabel("Role:"))
        layout.addWidget(role_combo)
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
            # Select current role in combo
            r_index = role_combo.findData(user.get("role", "admin"))
            if r_index >= 0:
                role_combo.setCurrentIndex(r_index)
            password_input.clear()

        user_combo.currentIndexChanged.connect(lambda _: sync_fields())
        # Prefer selection from Users page if available
        try:
            up = self.pages.get("users")
            sel = getattr(up, "selected_username", None)
            if sel:
                idx = user_combo.findText(sel)
                if idx >= 0:
                    user_combo.setCurrentIndex(idx)
        except Exception:
            pass
        def _sync_team_enabled() -> None:
            try:
                team_combo.setEnabled(role_combo.currentData() == "owner")
            except Exception:
                pass

        role_combo.currentIndexChanged.connect(lambda *_: _sync_team_enabled())
        sync_fields()
        _sync_team_enabled()

        def handle_update() -> None:
            user = user_combo.currentData()
            new_password = password_input.text().strip() or None
            new_team = team_combo.currentData()
            new_role = role_combo.currentData()
            try:
                if new_role == "owner" and not new_team:
                    QMessageBox.warning(dialog, "Error", "Select a team for the owner role")
                    return
                update_user(
                    user["username"],
                    new_password,
                    new_team,
                    data_dir / "users.txt",
                    new_role=new_role,
                )
            except ValueError as e:
                QMessageBox.warning(dialog, "Error", str(e))
                return
            QMessageBox.information(
                dialog, "Success", f"User {user['username']} updated."
            )
            dialog.accept()
            # Refresh Users page table if present
            try:
                up = self.pages.get("users")
                if up is not None and hasattr(up, "refresh"):
                    up.refresh()  # type: ignore[attr-defined]
            except Exception:
                pass

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
        # Prefer selected value from TeamsPage if available
        selected = None
        try:
            tp = self.pages.get("teams")
            if tp is not None and getattr(tp, "team_select", None) is not None:
                cur = tp.team_select.currentText().strip()
                if cur:
                    selected = cur
        except Exception:
            selected = None
        team_id = None
        if selected and selected in team_ids:
            team_id = selected
        else:
            team_id, ok = QInputDialog.getItem(
                self, "Open Team Dashboard", "Select a team:", team_ids, 0, False
            )
            if not ok:
                return
        if team_id:
            dashboard = OwnerDashboard(team_id)
            show_on_top(dashboard)
            self.team_dashboards.append(dashboard)

    def set_all_lineups(self) -> None:
        data_dir = get_base_dir() / "data"
        teams = load_teams(data_dir / "teams.csv")
        errors: list[str] = []
        for team in teams:
            try:
                auto_fill_lineup_for_team(
                    team.team_id,
                    players_file=data_dir / "players.csv",
                    roster_dir=data_dir / "rosters",
                    lineup_dir=data_dir / "lineups",
                )
            except Exception as exc:
                errors.append(f"{team.team_id}: {exc}")
        if errors:
            QMessageBox.warning(
                self,
                "Lineups Set (with issues)",
                "Some lineups could not be auto-filled:\n" + "\n".join(errors),
            )
        else:
            QMessageBox.information(self, "Lineups Set", "Lineups auto-filled for all teams.")
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
            try:
                if path.exists():
                    try:
                        path.chmod(0o644)  # ensure writable if previously locked
                    except OSError:
                        pass
                with path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for role, pid in assignments.items():
                        writer.writerow([pid, role])
            except PermissionError as exc:
                QMessageBox.warning(
                    self,
                    "Permission Denied",
                    f"Cannot write pitching roles to {path}.\n{exc}",
                )
                return
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
            # After reassignment, validate defensive coverage and warn if needed
            data_dir = get_base_dir() / "data"
            players = {p.player_id: p for p in load_players_from_csv(data_dir / "players.csv")}
            teams = load_teams(data_dir / "teams.csv")
            issues: list[str] = []
            for team in teams:
                try:
                    roster = load_roster(team.team_id)
                except FileNotFoundError:
                    continue
                missing = missing_positions(roster, players)
                if missing:
                    issues.append(f"{team.team_id}: {', '.join(missing)}")
            if issues:
                QMessageBox.warning(
                    self,
                    "Coverage Warnings",
                    "Some teams lack defensive coverage on the Active roster:\n"
                    + "\n".join(issues),
                )
            else:
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

    def reset_to_opening_day(self) -> None:
        """Reset league schedule and state to Opening Day.

        - Clears results/played/boxscore from `data/schedule.csv`
        - Resets `data/season_progress.json` to preseason-done and sim_index 0
        - Clears `data/standings.json`
        - Clears current year's draft state/results/pool files
        - Sets season phase to REGULAR_SEASON in `data/season_state.json`
        - Attempts to lock current rosters (best effort)
        - Optional: purge saved season boxscores under `data/boxscores/season`
        """
        confirm = QMessageBox.question(
            self,
            "Reset to Opening Day",
            (
                "This will clear all regular-season results and standings, "
                "and rewind the season to Opening Day. Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        base = get_base_dir() / "data"
        sched = base / "schedule.csv"
        progress = base / "season_progress.json"
        standings = base / "standings.json"
        stats_file = base / "season_stats.json"
        history_dir = base / "season_history"
        # Ask whether to purge season boxscores as well
        purge_box = (
            QMessageBox.question(
                self,
                "Purge Boxscores?",
                "Also delete saved season boxscores (data/boxscores/season)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

        # Require schedule to exist
        if not sched.exists():
            QMessageBox.warning(
                self,
                "No Schedule",
                "Cannot reset: schedule.csv not found. Generate a schedule first.",
            )
            return

        # 1) Load and rewrite schedule with cleared results
        try:
            rows: list[dict[str, str]] = []
            with sched.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for r in reader:
                    r = dict(r)
                    r["result"] = ""
                    r["played"] = ""
                    r["boxscore"] = ""
                    rows.append(r)
            # Preserve column order preferred by save_schedule
            fieldnames = ["date", "home", "away", "result", "played", "boxscore"]
            with sched.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow({
                        "date": r.get("date", ""),
                        "home": r.get("home", ""),
                        "away": r.get("away", ""),
                        "result": r.get("result", ""),
                        "played": r.get("played", ""),
                        "boxscore": r.get("boxscore", ""),
                    })
        except Exception as exc:
            QMessageBox.warning(self, "Reset Failed", f"Failed rewriting schedule: {exc}")
            return

        # Determine season year from first row (for draft flags)
        first_year: int | None = None
        try:
            if rows:
                first = rows[0]
                if first.get("date"):
                    first_year = int(str(first["date"]).split("-")[0])
        except Exception:
            first_year = None

        # 2) Reset progress file
        try:
            data: dict = {
                "preseason_done": {
                    "free_agency": True,
                    "training_camp": True,
                    "schedule": True,
                },
                "sim_index": 0,
                "playoffs_done": False,
            }
            # If existing progress has draft flags, preserve past years but remove current
            if progress.exists():
                import json as _json
                try:
                    cur = _json.loads(progress.read_text(encoding="utf-8"))
                    completed = set(cur.get("draft_completed_years", []))
                    if first_year is not None and first_year in completed:
                        completed.discard(first_year)
                    if completed:
                        data["draft_completed_years"] = sorted(completed)
                except Exception:
                    pass
            progress.parent.mkdir(parents=True, exist_ok=True)
            import json as _json2
            progress.write_text(_json2.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Reset Failed", f"Failed resetting progress: {exc}")
            return

        # 3) Clear standings
        try:
            standings.parent.mkdir(parents=True, exist_ok=True)
            standings.write_text("{}\n", encoding="utf-8")
        except Exception:
            # Not critical
            pass

        # 3b) Clear season stats (players and teams)
        try:
            stats_file.parent.mkdir(parents=True, exist_ok=True)
            # Remove existing stats and lock to ensure a clean slate
            # Also purge sharded daily history to prevent stale merges from
            # repopulating stats after reset.
            try:
                if history_dir.exists():
                    import shutil
                    shutil.rmtree(history_dir)
            except Exception:
                # Best effort only; continue with canonical file reset
                pass
            try:
                lock = stats_file.with_suffix(stats_file.suffix + ".lock")
                if lock.exists():
                    lock.unlink()
            except Exception:
                pass
            if stats_file.exists():
                try:
                    stats_file.unlink()
                except Exception:
                    pass
            stats_file.write_text(
                "{\n  \"players\": {},\n  \"teams\": {},\n  \"history\": []\n}\n",
                encoding="utf-8",
            )
        except Exception:
            # Not critical
            pass

        # 3c) Clear current year's draft state (pool, state, results)
        try:
            if first_year is not None:
                draft_files = [
                    f"draft_pool_{first_year}.json",
                    f"draft_pool_{first_year}.csv",
                    f"draft_state_{first_year}.json",
                    f"draft_results_{first_year}.csv",
                ]
                for name in draft_files:
                    p = base / name
                    try:
                        # Remove lock first if present
                        lock = p.with_suffix(p.suffix + ".lock")
                        if lock.exists():
                            lock.unlink()
                    except Exception:
                        pass
                    if p.exists():
                        try:
                            p.unlink()
                        except Exception:
                            pass
        except Exception:
            # Draft reset is best-effort; do not block overall reset
            pass

        # 4) Set phase to REGULAR_SEASON and attempt to lock rosters
        try:
            from playbalance.season_manager import SeasonManager, SeasonPhase

            mgr = SeasonManager()
            mgr.phase = SeasonPhase.REGULAR_SEASON
            mgr.save()
            try:
                mgr.finalize_rosters()
            except Exception:
                pass
            # Clear cached players so UI reloads fresh season stats immediately
            try:
                from utils.player_loader import load_players_from_csv as _lpf
                _lpf.cache_clear()  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception as exc:
            QMessageBox.warning(self, "Reset Partially Completed", f"State updated, but failed setting phase: {exc}")
            # Still continue to notify completion of the rest

        try:
            log_news_event("League reset to Opening Day")
        except Exception:
            pass

        # Optionally purge season boxscores
        if purge_box:
            try:
                import shutil
                box_dir = base / "boxscores" / "season"
                if box_dir.exists():
                    shutil.rmtree(box_dir)
                log_news_event("Purged saved season boxscores")
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Boxscore Purge Failed",
                    f"Reset completed, but failed to purge boxscores: {exc}",
                )

        QMessageBox.information(
            self,
            "Reset Complete",
            (
                "League reset to Opening Day." +
                (" Season boxscores purged." if purge_box else "")
            ),
        )

    def open_season_progress(self) -> None:
        win = SeasonProgressWindow(self)
        try:
            # Refresh status/date while sim is running and on close
            # Bind self as a default to avoid free-var scope issues in lambdas
            win.progressUpdated.connect(lambda *_, s=self: s._refresh_date_status())
            win.destroyed.connect(lambda *_, s=self: s._refresh_date_status())
        except Exception:
            pass
        win.show()

    def _refresh_date_status(self) -> None:
        try:
            # Update status bar and refresh current page if it supports refresh()
            # Determine current page key
            keys = list(self.pages.keys())
            idx = self.stack.currentIndex()
            key = keys[idx] if 0 <= idx < len(keys) else "home"
            self.statusBar().showMessage(self._status_with_date(f"Ready - {key.capitalize()}"))
            page = self.pages.get(key)
            if page is not None and hasattr(page, "refresh"):
                page.refresh()  # type: ignore[attr-defined]
        except Exception:
            # Best effort only
            pass

    def open_injury_center(self) -> None:
        try:
            win = InjuryCenterWindow(self)
            win.show()
        except Exception:
            pass

    def open_news_window(self) -> None:
        try:
            win = NewsWindow(self)
            win.show()
        except Exception:
            pass

    def open_free_agency(self) -> None:
        try:
            win = FreeAgencyWindow(self)
            win.show()
        except Exception:
            pass

    def open_playoffs_window(self) -> None:
        try:
            self._playoffs_win = PlayoffsWindow(self)
            self._playoffs_win.show()
        except Exception:
            # Headless environments may lack full Qt stack
            pass

    # ------------------------------------------------------------------
    # Amateur Draft helpers
    # ------------------------------------------------------------------
    def _compute_draft_date_for_year(self, year: int) -> str:
        import datetime as _dt
        d = _dt.date(year, 7, 1)
        while d.weekday() != 1:  # Tuesday is 1
            d += _dt.timedelta(days=1)
        d += _dt.timedelta(days=14)
        return d.isoformat()

    def _current_season_year(self) -> int:
        # Heuristic: attempt to read from schedule.csv if present; else use today
        try:
            from utils.path_utils import get_base_dir
            import csv as _csv
            sched = get_base_dir() / "data" / "schedule.csv"
            if sched.exists():
                with sched.open(newline="") as fh:
                    r = _csv.DictReader(fh)
                    first = next(r, None)
                    if first and first.get("date"):
                        return int(str(first["date"]).split("-")[0])
        except Exception:
            pass
        from datetime import date as _date
        return _date.today().year

    def _open_draft_console(self) -> None:
        try:
            from ui.draft_console import DraftConsole
        except Exception as exc:
            QMessageBox.warning(self, "Draft Console", f"Unable to open Draft Console: {exc}")
            return
        year = self._current_season_year()
        date_str = self._compute_draft_date_for_year(year)
        dlg = DraftConsole(date_str, self)
        dlg.exec()

    def open_draft_console(self) -> None:
        self._open_draft_console()

    def open_draft_pool(self) -> None:
        # For now, open the same console; users can browse pool without drafting
        self._open_draft_console()

    def open_draft_results(self) -> None:
        """Open a simple viewer for current season's draft results CSV, if present."""
        import csv as _csv
        year = self._current_season_year()
        from utils.path_utils import get_base_dir as _gb
        p = _gb() / "data" / f"draft_results_{year}.csv"
        if not p.exists():
            QMessageBox.information(self, "Draft Results", f"No draft results found for {year}.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Draft Results {year}")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        label = QLabel(str(p))
        lay.addWidget(label)
        lst = QListWidget()
        try:
            with p.open(newline="", encoding="utf-8") as fh:
                r = _csv.DictReader(fh)
                for row in r:
                    rd = row.get("round", "")
                    pick = row.get("overall_pick", "")
                    team = row.get("team_id", "")
                    pid = row.get("player_id", "")
                    lst.addItem(f"R{rd} P{pick}: {team} -> {pid}")
        except Exception:
            lst.addItem("<Unable to read draft results>")
        lay.addWidget(lst)
        show_on_top(dlg)

    def open_draft_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Draft Settings")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        cfg = load_draft_config()

        layout.addWidget(QLabel("Rounds:"))
        rounds_input = QLineEdit(str(cfg.get("rounds", 10)))
        layout.addWidget(rounds_input)

        layout.addWidget(QLabel("Pool Size:"))
        pool_input = QLineEdit(str(cfg.get("pool_size", 200)))
        layout.addWidget(pool_input)

        layout.addWidget(QLabel("Random Seed (blank = default):"))
        seed_val = cfg.get("seed")
        seed_input = QLineEdit("" if seed_val in (None, "") else str(seed_val))
        layout.addWidget(seed_input)

        row = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        row.addWidget(save_btn)
        row.addWidget(cancel_btn)
        layout.addLayout(row)

        def do_save() -> None:
            try:
                rounds = int(rounds_input.text().strip())
                pool_size = int(pool_input.text().strip())
            except ValueError:
                QMessageBox.warning(dialog, "Invalid Input", "Rounds and Pool Size must be integers.")
                return
            seed_txt = seed_input.text().strip()
            seed: int | None
            if seed_txt == "":
                seed = None
            else:
                try:
                    seed = int(seed_txt)
                except ValueError:
                    QMessageBox.warning(dialog, "Invalid Seed", "Seed must be an integer or blank.")
                    return
            try:
                save_draft_config({"rounds": rounds, "pool_size": pool_size, "seed": seed})
                QMessageBox.information(dialog, "Saved", "Draft settings saved. New drafts will use these settings.")
                dialog.accept()
            except Exception as exc:
                QMessageBox.warning(dialog, "Save Failed", str(exc))

        save_btn.clicked.connect(do_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.setLayout(layout)
        dialog.exec()

    # Draft gating ------------------------------------------------------
    def _refresh_draft_page(self) -> None:
        try:
            dp = self.pages.get("draft")
            if dp is None:
                return
            available, cur_date, draft_date, completed = self._draft_availability_details()
            # Gate only pool and draft console; keep settings always enabled
            dp.view_draft_pool_button.setEnabled(available)
            dp.start_resume_draft_button.setEnabled(available)
            dp.draft_settings_button.setEnabled(True)
            try:
                dp.view_results_button.setVisible(bool(completed))
                dp.view_results_button.setEnabled(bool(completed))
            except Exception:
                pass
            # Status message
            if completed:
                msg = f"Current date: {cur_date} | Draft Day: {draft_date} | Draft already completed this year"
            elif cur_date and draft_date:
                msg = (
                    f"Current date: {cur_date} | Draft Day: {draft_date} | "
                    f"Status: {'Ready' if available else 'Not yet'}"
                )
            else:
                msg = "Draft status unavailable - missing schedule or progress data"
            try:
                dp.draft_status_label.setText(msg)
                # Update tooltips to mirror availability and guidance
                if completed:
                    tip = "Draft already completed for this season."
                elif cur_date and draft_date:
                    tip = (
                        f"Draft Day: {draft_date}. Current date: {cur_date}. "
                        f"{'Ready to open the Draft Console.' if available else 'Buttons enable on Draft Day.'}"
                    )
                else:
                    tip = "Draft timing unknown. Ensure schedule and season progress exist."
                dp.view_draft_pool_button.setToolTip(tip)
                dp.start_resume_draft_button.setToolTip(tip)
                dp.draft_settings_button.setToolTip("Configure rounds, pool size, and RNG seed (always available).")
                if completed:
                    dp.view_results_button.setToolTip("Open draft results for the current season.")
            except Exception:
                pass
        except Exception:
            pass

    def _is_draft_available(self) -> bool:
        from utils.path_utils import get_base_dir
        import csv as _csv
        import json as _json
        from datetime import date as _date
        base = get_base_dir() / "data"
        sched = base / "schedule.csv"
        prog = base / "season_progress.json"
        if not sched.exists() or not prog.exists():
            return False
        try:
            with prog.open("r", encoding="utf-8") as fh:
                progress = _json.load(fh)
        except Exception:
            return False
        with sched.open(newline="") as fh:
            rows = list(_csv.DictReader(fh))
        if not rows:
            return False
        sim_index = int(progress.get("sim_index", 0) or 0)
        sim_index = max(0, min(sim_index, len(rows) - 1))
        cur_date = str(rows[sim_index].get("date") or "")
        if not cur_date:
            return False
        year = int(cur_date.split("-")[0])
        done = set(progress.get("draft_completed_years", []))
        if year in done:
            return False
        draft_date = self._compute_draft_date_for_year(year)
        try:
            y1, m1, d1 = [int(x) for x in cur_date.split("-")]
            y2, m2, d2 = [int(x) for x in draft_date.split("-")]
            return _date(y1, m1, d1) >= _date(y2, m2, d2)
        except Exception:
            return False

    def _draft_availability_details(self) -> tuple[bool, str | None, str | None, bool]:
        """Return (available, current_date, draft_date, completed) with safe fallbacks."""
        from utils.path_utils import get_base_dir
        import csv as _csv
        import json as _json
        from datetime import date as _date
        base = get_base_dir() / "data"
        sched = base / "schedule.csv"
        prog = base / "season_progress.json"
        if not sched.exists() or not prog.exists():
            return (False, None, None, False)
        try:
            with prog.open("r", encoding="utf-8") as fh:
                progress = _json.load(fh)
        except Exception:
            progress = {}

        cur_date = get_current_sim_date()
        if not cur_date:
            try:
                with sched.open(newline="") as fh:
                    rows = list(_csv.DictReader(fh))
                first = next((r for r in rows if r.get("date")), None)
                cur_date = str(first.get("date")) if first else ""
            except Exception:
                cur_date = ""
        if not cur_date:
            return (False, None, None, False)

        year = int(cur_date.split("-")[0])
        draft_date = self._compute_draft_date_for_year(year)
        done = set(progress.get("draft_completed_years", [])) if isinstance(progress, dict) else set()
        completed = year in done
        try:
            y1, m1, d1 = [int(x) for x in cur_date.split("-")]
            y2, m2, d2 = [int(x) for x in draft_date.split("-")]
            available = (not completed) and (_date(y1, m1, d1) >= _date(y2, m2, d2))
        except Exception:
            available = False
        return (available, cur_date, draft_date, completed)


__all__ = [
    "MainWindow",
    "LeaguePage",
    "TeamsPage",
    "UsersPage",
    "UtilitiesPage",
]


