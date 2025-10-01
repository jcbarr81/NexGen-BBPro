from __future__ import annotations

import csv
from datetime import datetime
from typing import Dict

from PyQt6.QtCore import Qt
try:
    from PyQt6.QtGui import QAction, QFont, QPixmap, QIcon
except ImportError:  # pragma: no cover - support test stubs
    from PyQt6.QtGui import QFont, QPixmap
    from PyQt6.QtWidgets import QAction
    QIcon = None  # type: ignore[assignment]
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
from utils.team_loader import load_teams
from utils.path_utils import get_base_dir
from utils.sim_date import get_current_sim_date
from utils.roster_validation import missing_positions
from ui.window_utils import show_on_top


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

        logo_path = get_base_dir() / "logo" / "teams" / f"{team_id.lower()}.png"
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
            from pathlib import Path
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
        self.pages = {
            "home": OwnerHomePage(self),
            "roster": RosterPage(self),
            "team": TeamPage(self),
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
        self.btn_home.clicked.connect(lambda: self._go("home"))
        self.btn_roster.clicked.connect(lambda: self._go("roster"))
        self.btn_team.clicked.connect(lambda: self._go("team"))
        self.btn_transactions.clicked.connect(lambda: self._go("transactions"))
        self.btn_league.clicked.connect(lambda: self._go("league"))
        self.btn_home.setChecked(True)
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

    def _go(self, key: str) -> None:
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        btn = self.nav_buttons.get(key)
        if btn:
            btn.setChecked(True)
        idx = list(self.pages.keys()).index(key)
        self.stack.setCurrentIndex(idx)
        date_str = get_current_sim_date()
        suffix = f" | Date: {date_str}" if date_str else ""
        self.statusBar().showMessage(f"Ready • {key.capitalize()}" + suffix)
        # Refresh page if it supports a refresh() hook
        page = self.pages.get(key)
        if page is not None and hasattr(page, "refresh"):
            try:
                page.refresh()  # type: ignore[attr-defined]
            except Exception:
                pass
        # Update header scoreboard context on navigation
        try:
            self._update_header_context()
        except Exception:
            pass

    # ---------- Actions used by pages ----------
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
        """Compute lightweight metrics for display on the Home page.

        Returns keys: record (e.g., '10-8'), run_diff ('+12'/'-3'/'0'),
        next_opponent (e.g., 'vs BOS'), next_date (ISO date or '--'),
        streak (e.g., 'W3'), last10 (e.g., '7-3'), injuries (int), prob_sp (name/id).
        """
        from utils.path_utils import get_base_dir
        from utils.standings_utils import normalize_record
        import json
        import csv

        team_id = getattr(self, "team_id", None)
        base = get_base_dir() / "data"

        # Record, run diff, streak and last10 from standings.json
        record_str = "--"
        run_diff_str = "--"
        streak_str = "--"
        last10_str = "--"
        standings_path = base / "standings.json"
        try:
            raw = {}
            if standings_path.exists():
                with standings_path.open("r", encoding="utf-8") as fh:
                    raw = json.load(fh) or {}
            rec = normalize_record(raw.get(team_id)) if team_id else None
            if rec:
                wins = int(rec.get("wins", 0))
                losses = int(rec.get("losses", 0))
                record_str = f"{wins}-{losses}"
                rd = int(rec.get("runs_for", 0)) - int(rec.get("runs_against", 0))
                run_diff_str = f"{rd:+d}"
                # streak
                st = rec.get("streak", {}) or {}
                res = st.get("result")
                length = int(st.get("length", 0) or 0)
                if res in {"W", "L"} and length > 0:
                    streak_str = f"{res}{length}"
                # last10
                l10 = rec.get("last10", []) or []
                if isinstance(l10, list) and l10:
                    w = sum(1 for x in l10 if str(x).upper().startswith("W"))
                    l = sum(1 for x in l10 if str(x).upper().startswith("L"))
                    last10_str = f"{w}-{l}"
        except Exception:
            pass

        # Next game info from schedule.csv and current sim date
        next_opp = "--"
        next_date = "--"
        sched = base / "schedule.csv"
        try:
            cur_date = get_current_sim_date()
            rows: list[dict[str, str]] = []
            if sched.exists():
                with sched.open(newline="", encoding="utf-8") as fh:
                    rows = list(csv.DictReader(fh))
            # Filter games for this team
            games = [r for r in rows if r.get("home") == team_id or r.get("away") == team_id]
            # Prefer next unplayed game on/after current date
            def key_date(row: dict[str, str]) -> str:
                return str(row.get("date") or "9999-12-31")
            games.sort(key=key_date)
            target = None
            if games:
                if cur_date:
                    for g in games:
                        date_val = str(g.get("date") or "")
                        res = str(g.get("result") or "")
                        if date_val >= cur_date and not res:
                            target = g
                            break
                    if target is None:
                        # fallback: first game on/after current date
                        for g in games:
                            if str(g.get("date") or "") >= cur_date:
                                target = g
                                break
                if target is None:
                    # fallback: first future unplayed regardless of date
                    for g in games:
                        if not str(g.get("result") or ""):
                            target = g
                            break
                if target is None:
                    # fallback: last game (season over)
                    target = games[-1]
            if target:
                if target.get("home") == team_id:
                    next_opp = f"vs {target.get('away','--')}"
                else:
                    next_opp = f"at {target.get('home','--')}"
                next_date = str(target.get("date") or "--")
        except Exception:
            pass

        # Injuries from roster DL/IR (best-effort)
        injuries = 0
        try:
            injuries = len(getattr(self.roster, "dl", []) or []) + len(getattr(self.roster, "ir", []) or [])
        except Exception:
            injuries = 0

        # Probable starter: highest endurance SP on active roster
        prob_sp = "--"
        try:
            act_ids = set(getattr(self.roster, "act", []) or [])
            sps = []
            for pid, p in (self.players or {}).items():
                if pid in act_ids and (getattr(p, "is_pitcher", False) or str(getattr(p, "primary_position", "")).upper() == "P"):
                    if (getattr(p, "role", "") or get_role(p)) == "SP":
                        sps.append(p)
            if sps:
                cand = max(sps, key=lambda x: int(getattr(x, "endurance", 0) or 0))
                prob_sp = f"{getattr(cand,'first_name','')} {getattr(cand,'last_name','')}".strip() or getattr(cand, 'player_id', '--')
        except Exception:
            pass

        return {
            "record": record_str,
            "run_diff": run_diff_str,
            "next_opponent": next_opp,
            "next_date": next_date,
            "streak": streak_str,
            "last10": last10_str,
            "injuries": injuries,
            "prob_sp": prob_sp,
        }

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
        text = (
            f"Next: {opp} {date} | Record {rec} RD {rd} | "
            f"Stk {streak} L10 {last10} | Inj {injuries} | Prob SP {prob}"
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
