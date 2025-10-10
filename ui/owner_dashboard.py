from __future__ import annotations

import csv
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import Qt
try:
    from PyQt6.QtGui import QAction, QFont, QPixmap, QIcon
except ImportError:  # pragma: no cover - support test stubs
    from PyQt6.QtGui import QFont, QPixmap
    from PyQt6.QtWidgets import QAction
    QIcon = None  # type: ignore[assignment]
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .components import NavButton
from .theme import _toggle_theme
from .roster_page import RosterPage
from .transactions_page import TransactionsPage
from .schedule_page import SchedulePage
from .team_page import TeamPage
from .owner_home_page import OwnerHomePage
from .lineup_editor import LineupEditor
from .pitching_editor import PitchingEditor
from .position_players_dialog import PositionPlayersDialog
from .pitchers_dialog import PitchersDialog
from .reassign_players_dialog import ReassignPlayersDialog
from .transactions_window import TransactionsWindow
from .trade_dialog import TradeDialog
from .standings_window import StandingsWindow
from .schedule_window import ScheduleWindow
from .team_schedule_window import TeamScheduleWindow, SCHEDULE_FILE
from .team_stats_window import TeamStatsWindow
from .league_stats_window import LeagueStatsWindow
from .league_leaders_window import LeagueLeadersWindow
from .news_window import NewsWindow
from .player_browser_dialog import PlayerBrowserDialog
from utils.roster_loader import load_roster
from utils.player_loader import load_players_from_csv
from utils.free_agent_finder import find_free_agents
from utils.pitcher_role import get_role
from utils.team_loader import load_teams, save_team_settings
from utils.path_utils import get_base_dir
from utils.sim_date import get_current_sim_date
from ui.analytics import gather_owner_quick_metrics
from ui.dashboard_core import DashboardContext, NavigationController, PageRegistry
from ui.window_utils import show_on_top
from ui.sim_date_bus import sim_date_bus


class OwnerDashboard(QMainWindow):
    """Owner-facing dashboard with sidebar navigation."""

    def __init__(self, team_id: str):
        super().__init__()
        self.team_id = team_id
        self.players: Dict[str, object] = {
            p.player_id: p for p in load_players_from_csv("data/players.csv")
        }
        self.roster = load_roster(team_id)
        teams = load_teams()
        self.team = next((t for t in teams if t.team_id == team_id), None)

        base_path = get_base_dir()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._background_futures: set[Future[Any]] = set()
        self._cleanup_callbacks: list[Callable[[], None]] = []
        self._context = DashboardContext(
            base_path=base_path,
            run_async=self._submit_background,
            show_toast=self._show_toast,
            register_cleanup=self._register_cleanup,
        )
        self.context = self._context
        self._latest_metrics: Dict[str, Any] = {}
        self._registry = PageRegistry()
        self._nav_controller = NavigationController(self._registry)
        self._nav_controller.add_listener(self._on_nav_changed)

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

        logo_path = base_path / "logo" / "teams" / f"{team_id.lower()}.png"
        if logo_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path)).scaledToWidth(
                96, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            side.addWidget(logo_label)

        brand = QLabel(f"⚾  {team_id} Owner")
        brand.setStyleSheet("font-weight:900; font-size:16px;")
        side.addWidget(brand)

        self.btn_home = NavButton("  Dashboard")
        self.btn_roster = NavButton("  Roster")
        self.btn_team = NavButton("  Team")
        self.btn_transactions = NavButton("  Moves & Trades")
        self.btn_league = NavButton("  League Hub")

        for b in (self.btn_home, self.btn_roster, self.btn_team, self.btn_transactions, self.btn_league):
            side.addWidget(b)

        self.nav_buttons = {
            "home": self.btn_home,
            "roster": self.btn_roster,
            "team": self.btn_team,
            "transactions": self.btn_transactions,
            "league": self.btn_league,
        }

        side.addStretch()
        self.btn_settings = NavButton("  Toggle Theme")
        self.btn_settings.clicked.connect(lambda: _toggle_theme(self.statusBar()))
        side.addWidget(self.btn_settings)

        # Nav icons and tooltips (best-effort)
        try:
            icon_dir = Path(__file__).resolve().parent / "icons"
            def _set(btn, name: str, tip: str) -> None:
                try:
                    if QIcon is not None:
                        btn.setIcon(QIcon(str(icon_dir / name)))
                        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                except Exception:
                    pass
                btn.setToolTip(tip)
            _set(self.btn_home, "team_dashboard.svg", "Overview and quick actions")
            _set(self.btn_roster, "team_dashboard.svg", "Roster and player tools")
            _set(self.btn_team, "season_progress.svg", "Team schedule and stats")
            _set(self.btn_transactions, "review_trades.svg", "Transactions and trades")
            _set(self.btn_league, "season_progress.svg", "League schedule, standings, stats")
        except Exception:
            pass

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
        self.pages: Dict[str, QWidget] = {}
        self._register_pages()

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
        try:
            self.setWindowState(Qt.WindowState.WindowMaximized)
        except Exception:
            pass

        self._build_menu()
        self._sim_date_bus = sim_date_bus()
        try:
            self._sim_date_bus.dateChanged.connect(self._on_sim_date_changed)
        except Exception:
            pass

        # Navigation signals
        self.btn_home.clicked.connect(lambda: self._go("home"))
        self.btn_roster.clicked.connect(lambda: self._go("roster"))
        self.btn_team.clicked.connect(lambda: self._go("team"))
        self.btn_transactions.clicked.connect(lambda: self._go("transactions"))
        self.btn_league.clicked.connect(lambda: self._go("league"))
        self._go("home")

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
        news_action = QAction("News Feed", self)
        news_action.triggered.connect(self.open_news_window)
        view_menu.addAction(news_action)
        try:
            settings_action = QAction("Team Settings", self)
            settings_action.triggered.connect(self.open_team_settings_dialog)
            view_menu.addAction(settings_action)
        except Exception:
            pass

    def _register_pages(self) -> None:
        factories: Dict[str, Callable[[DashboardContext], QWidget]] = {
            "home": lambda ctx: OwnerHomePage(self),
            "roster": lambda ctx: RosterPage(self),
            "team": lambda ctx: TeamPage(self),
            "transactions": lambda ctx: TransactionsPage(self),
            "league": lambda ctx: SchedulePage(self),
        }
        for key, factory in factories.items():
            self._registry.register(key, factory)
            widget = self._registry.build(key, self._context)
            self.pages[key] = widget
            self.stack.addWidget(widget)


    def _submit_background(self, worker: Callable[[], Any]) -> Future[Any]:
        future = self._executor.submit(worker)
        self._background_futures.add(future)

        def _cleanup(fut: Future[Any]) -> None:
            self._background_futures.discard(fut)

        future.add_done_callback(_cleanup)
        return future

    def _register_cleanup(self, callback: Callable[[], None]) -> None:
        if callback not in self._cleanup_callbacks:
            self._cleanup_callbacks.append(callback)

    def _show_toast(self, kind: str, message: str) -> None:
        prefixes = {
            "success": "SUCCESS",
            "error": "ERROR",
            "warning": "WARN",
            "info": "INFO",
        }
        prefix = prefixes.get(kind, kind.upper())
        try:
            self.statusBar().showMessage(f"[{prefix}] {message}", 5000)
        except Exception:
            pass


    def _go(self, key: str) -> None:
        if key not in self.pages:
            return
        try:
            self._nav_controller.set_current(key)
        except KeyError:
            return

    def _on_nav_changed(self, key: Optional[str]) -> None:
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == key)
        if key is None:
            return
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self._update_status_bar(key)
        refresh = getattr(page, 'refresh', None)
        if callable(refresh):
            try:
                refresh()
            except Exception:
                pass
        try:
            self._update_header_context()
        except Exception:
            pass

    def _update_status_bar(self, key: Optional[str] = None) -> None:
        """Render the status bar message with the current sim date."""

        if key is None:
            key = self._nav_controller.current_key or "home"
        label = key.capitalize() if isinstance(key, str) else "Home"
        date_str = get_current_sim_date()
        suffix = f" | Date: {date_str}" if date_str else ""
        try:
            self.statusBar().showMessage(f"Ready - {label}{suffix}")
        except Exception:
            pass

    def _on_sim_date_changed(self, _value: object) -> None:
        """Update status bar and metrics when the sim date advances."""

        try:
            self._update_status_bar()
        except Exception:
            pass
        try:
            self._update_header_context()
        except Exception:
            pass

    def open_lineup_editor(self) -> None:
        show_on_top(LineupEditor(self.team_id))

    def open_pitching_editor(self) -> None:
        show_on_top(PitchingEditor(self.team_id))

    def open_position_players_dialog(self) -> None:
        show_on_top(PositionPlayersDialog(self.players, self.roster))

    def open_pitchers_dialog(self) -> None:
        show_on_top(PitchersDialog(self.players, self.roster))

    def open_player_browser_dialog(self) -> None:
        show_on_top(PlayerBrowserDialog(self.players, self.roster, self))

    def open_reassign_players_dialog(self) -> None:
        show_on_top(ReassignPlayersDialog(self.players, self.roster, self))

    def open_transactions_page(self) -> None:
        show_on_top(TransactionsWindow(self.team_id))

    def open_trade_dialog(self) -> None:
        show_on_top(TradeDialog(self.team_id, self))

    def open_roster_page(self) -> None:
        """Switch the main view to the roster page."""
        self._go("roster")

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
        show_on_top(StandingsWindow(self))

    def open_schedule_window(self) -> None:
        show_on_top(ScheduleWindow(self))

    def open_team_schedule_window(self) -> None:
        if not getattr(self, "team_id", None):
            QMessageBox.warning(self, "Error", "Team information not available.")
            return
        has_games = False
        if SCHEDULE_FILE.exists():
            with SCHEDULE_FILE.open(newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if row.get("home") == self.team_id or row.get("away") == self.team_id:
                        has_games = True
                        break
        if not has_games:
            QMessageBox.information(self, "Schedule", "No schedule available for this team.")
            return
        show_on_top(TeamScheduleWindow(self.team_id, self))

    def open_team_stats_window(self, tab: str = "team") -> None:
        """Open the team statistics window with the specified default tab."""
        if not getattr(self, "team", None):
            QMessageBox.warning(self, "Error", "Team information not available.")
            return
        w = TeamStatsWindow(self.team, self.players, self.roster, self)
        index_map = {"batting": 0, "pitching": 1, "team": 2}
        if isinstance(tab, bool) or tab is None:
            tab_name = "team"
        else:
            tab_name = str(tab).lower()
        w.tabs.setCurrentIndex(index_map.get(tab_name, 2))
        show_on_top(w)

    def open_league_stats_window(self) -> None:
        teams = load_teams()
        show_on_top(LeagueStatsWindow(teams, self.players.values(), self))

    def open_league_leaders_window(self) -> None:
        show_on_top(LeagueLeadersWindow(self.players.values(), self))

    def open_news_window(self) -> None:
        try:
            show_on_top(NewsWindow(self))
        except Exception:
            pass

    def open_team_settings_dialog(self) -> None:
        """Open the Team Settings dialog for the current team and persist changes."""
        try:
            if not getattr(self, "team", None):
                QMessageBox.warning(self, "Team Settings", "No team loaded for this owner.")
                return
            from ui.team_settings_dialog import TeamSettingsDialog
            dlg = TeamSettingsDialog(self.team, self)
            if dlg.exec():
                data = dlg.get_settings()
                # Update the in-memory team and persist to CSV
                self.team.primary_color = data.get("primary_color", self.team.primary_color) or self.team.primary_color
                self.team.secondary_color = data.get("secondary_color", self.team.secondary_color) or self.team.secondary_color
                self.team.stadium = data.get("stadium", self.team.stadium) or self.team.stadium
                save_team_settings(self.team)
                QMessageBox.information(self, "Team Settings", "Team settings saved.")
                # Notify pages to refresh if they implement refresh()
                try:
                    for p in self.pages.values():
                        if hasattr(p, "refresh"):
                            p.refresh()  # type: ignore[attr-defined]
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Team Settings", f"Failed to update settings: {e}")

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

    # ---------- Metrics for Home page and header ----------
    def get_quick_metrics(self) -> dict:
        """Return cached metrics for the header and home page."""
        try:
            metrics = gather_owner_quick_metrics(
                self.team_id,
                base_path=self.context.base_path,
                roster=self.roster,
                players=self.players,
            )
        except Exception:
            metrics = {}
        self._latest_metrics = metrics
        return metrics

    def closeEvent(self, event) -> None:  # type: ignore[override]
        for callback in list(self._cleanup_callbacks):
            try:
                callback()
            except Exception:
                pass
        for fut in list(self._background_futures):
            try:
                fut.cancel()
            except Exception:
                pass
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass
        try:
            if hasattr(self, "_sim_date_bus"):
                self._sim_date_bus.dateChanged.disconnect(self._on_sim_date_changed)
        except Exception:
            pass
        super().closeEvent(event)

    def _update_header_context(self) -> None:
        """Update header scoreboard label with quick context."""
        metrics = self.get_quick_metrics()
        rec = metrics.get("record", "--")
        rd = metrics.get("run_diff", "--")
        opp = metrics.get("next_opponent", "--")
        date = metrics.get("next_date", "--")
        streak = metrics.get("streak", "--")
        last10 = metrics.get("last10", "--")
        injuries = metrics.get("injuries", 0)
        prob = metrics.get("prob_sp", "--")
        bullpen = metrics.get("bullpen", {}) or {}
        bp_ready = int(bullpen.get("ready", 0) or 0)
        bp_total = int(bullpen.get("total", 0) or 0)
        bp_summary = f"{bp_ready}/{bp_total}" if bp_total else "--"
        trend_series = ((metrics.get("trends") or {}).get("series") or {})
        win_pct_series = trend_series.get("win_pct") or []
        win_pct = f"{win_pct_series[-1]:.3f}" if win_pct_series else "--"
        text = (
            f"Next: {opp} {date} | Record {rec} RD {rd} | "
            f"Stk {streak} L10 {last10} | Inj {injuries} | Prob SP {prob} | "
            f"BP {bp_summary} | Win% {win_pct}"
        )
        try:
            self.scoreboard.setText(text)
        except Exception:
            pass
        # Update roster nav tooltip with coverage summary
        try:
            miss = missing_positions(self.roster, self.players)
            if miss:
                self.btn_roster.setToolTip("Missing coverage: " + ", ".join(miss))
            else:
                self.btn_roster.setToolTip("Defensive coverage looks good.")
        except Exception:
            pass
