from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QMessageBox,
        QListWidget,
        QListWidgetItem,
    )
    from PyQt6.QtGui import QColor
except ImportError:  # pragma: no cover - test stubs
    class _WidgetDummy:
        def __init__(self, *args, **kwargs) -> None:
            if 'DummySignal' in globals():
                self.clicked = DummySignal(self)
            else:
                self.clicked = None

        def __getattr__(self, name):
            def _noop(*_args, **_kwargs):
                return None

            return _noop

    class _ListWidgetDummy(_WidgetDummy):
        class SelectionMode:
            NoSelection = 0

    QDialog = QLabel = QPushButton = QVBoxLayout = QMessageBox = _WidgetDummy
    QListWidget = _ListWidgetDummy
    QListWidgetItem = _WidgetDummy

    class QColor:  # type: ignore[too-many-ancestors]
        def __init__(self, *args, **kwargs) -> None:
            pass

try:
    from PyQt6.QtCore import pyqtSignal, QTimer, QThread
except Exception:  # pragma: no cover - fallback for headless tests
    class _DummySignal:
        def __init__(self, *args, **kwargs):
            pass

        def emit(self, *args, **kwargs):
            pass

        def connect(self, *args, **kwargs):
            pass

    def pyqtSignal(*args, **kwargs):  # type: ignore
        return _DummySignal()
    class QTimer:  # type: ignore
        @staticmethod
        def singleShot(ms: int, callback: Callable[[], None]) -> None:
            callback()
    QThread = None  # type: ignore

try:  # pragma: no cover - fallback for environments without PyQt6
    from PyQt6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - simple stub for tests
    class QApplication:  # type: ignore
        @staticmethod
        def processEvents() -> None:  # pragma: no cover - no-op
            pass
from datetime import date
import csv
import json
from pathlib import Path

import playbalance.season_manager as season_manager
from playbalance.aging_model import age_and_retire
from playbalance.season_manager import SeasonManager, SeasonPhase
from playbalance.training_camp import run_training_camp
from services.free_agency import list_unsigned_players
from playbalance.season_simulator import SeasonSimulator
from ui.draft_console import DraftConsole
from playbalance.schedule_generator import generate_mlb_schedule, save_schedule
from utils.exceptions import DraftRosterError
from playbalance.simulation import save_boxscore_html
from utils.news_logger import log_news_event
from utils.team_loader import load_teams
from utils.standings_utils import default_record, normalize_record, update_record
from playbalance.config import load_config as load_pb_config
from playbalance.benchmarks import load_benchmarks as load_pb_benchmarks
from playbalance.orchestrator import (
    simulate_day as pb_simulate_day,
    simulate_week as pb_simulate_week,
    simulate_month as pb_simulate_month,
)
from utils.team_loader import load_teams
from utils.roster_loader import load_roster
from utils.lineup_loader import load_lineup
from utils.player_loader import load_players_from_csv
from utils.pitcher_role import get_role
from utils.sim_date import get_current_sim_date
from ui.sim_date_bus import notify_sim_date_changed


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TEAMS_FILE = DATA_DIR / "teams.csv"
SCHEDULE_FILE = DATA_DIR / "schedule.csv"
PROGRESS_FILE = DATA_DIR / "season_progress.json"


class SeasonProgressWindow(QDialog):
    """Dialog displaying the current season phase and progress notes."""

    # Emitted whenever season progress persists a new date, or when closing
    # the window. Carries the latest current sim date string.
    _simStatusRequested = pyqtSignal(object)
    progressUpdated = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        schedule: list[dict[str, str]] | None = None,
        simulate_game=None,
        *,
        run_async: Optional[Callable[[Callable[[], Any]], Any]] = None,
        show_toast: Optional[Callable[[str, str], None]] = None,
        register_cleanup: Optional[Callable[[Callable[[], None]], None]] = None,
    ) -> None:
        super().__init__(parent)
        try:
            self.setWindowTitle("Season Progress")
            self.setMinimumSize(320, 280)
        except Exception:  # pragma: no cover - harmless in headless tests
            pass

        self._run_async = run_async
        self._show_toast = show_toast
        self._register_cleanup = register_cleanup
        self._active_future = None
        self._executor: ThreadPoolExecutor | None = None
        if self._run_async is None:
            executor = ThreadPoolExecutor(max_workers=1)
            self._executor = executor
            self._run_async = executor.submit
            if self._register_cleanup is not None:
                try:
                    self._register_cleanup(lambda ex=executor: ex.shutdown(wait=False))
                except Exception:
                    pass

        self.manager = SeasonManager()
        self._simulate_game = simulate_game
        if schedule is None and SCHEDULE_FILE.exists():
            with SCHEDULE_FILE.open(newline="") as fh:
                reader = csv.DictReader(fh)
                schedule = list(reader)
        # Persist league data after each game so that standings, schedules and
        # statistics remain current even if a simulation run is interrupted.
        # Compute Draft Day from schedule (third Tuesday in July)
        draft_date = self._compute_draft_date((schedule or [{}])[0].get("date") if schedule else None)
        self._draft_date = draft_date
        if simulate_game is not None:
            self.simulator = SeasonSimulator(
                schedule or [],
                simulate_game,
                on_draft_day=self._on_draft_day,
                draft_date=draft_date,
                after_game=self._record_game,
            )
        else:
            self.simulator = SeasonSimulator(
                schedule or [],
                on_draft_day=self._on_draft_day,
                draft_date=draft_date,
                after_game=self._record_game,
            )
        self._cancel_requested = False
        # Track season standings with detailed splits so that schedule and
        # standings windows can display rich statistics.
        standings_file = DATA_DIR / "standings.json"
        raw_standings: dict[str, dict[str, object]] = {}
        if standings_file.exists():
            try:
                with standings_file.open("r", encoding="utf-8") as fh:
                    raw_standings = json.load(fh)
            except (OSError, json.JSONDecodeError):
                raw_standings = {}
        self._standings: dict[str, dict[str, object]] = {
            team_id: normalize_record(data)
            for team_id, data in raw_standings.items()
        }
        teams = load_teams()
        self._team_divisions = {team.team_id: team.division for team in teams}
        self._preseason_done = {
            "free_agency": False,
            "training_camp": False,
            "schedule": False,
        }
        self._playoffs_done = False
        self._load_progress()

        try:
            self._pb_cfg = load_pb_config()
            self._pb_benchmarks = load_pb_benchmarks()
        except Exception:  # pragma: no cover - configuration optional
            self._pb_cfg = None
            self._pb_benchmarks = {}

        # Validate schedule team IDs against known teams; offer to regenerate
        try:
            self._ensure_valid_schedule_teams()
        except Exception:
            # Best-effort validation; proceed if any issues in headless envs
            pass

        layout = QVBoxLayout(self)

        self.phase_label = QLabel()
        layout.addWidget(self.phase_label)

        # Always-visible indicator of the current simulation date
        self.date_label = QLabel()
        layout.addWidget(self.date_label)

        self.notes_label = QLabel()
        self.notes_label.setWordWrap(True)
        layout.addWidget(self.notes_label)

        self.timeline_label = QLabel("Season Timeline")
        self.timeline_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.timeline_label)

        self.timeline = QListWidget()
        self.timeline.setMouseTracking(True)
        self.timeline.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.timeline)

        # Actions available during the preseason
        self.free_agency_button = QPushButton("List Unsigned Players")
        self.free_agency_button.clicked.connect(self._show_free_agents)
        layout.addWidget(self.free_agency_button)

        self.training_camp_button = QPushButton("Run Training Camp")
        self.training_camp_button.clicked.connect(self._run_training_camp)
        layout.addWidget(self.training_camp_button)

        self.generate_schedule_button = QPushButton("Generate Schedule")
        self.generate_schedule_button.clicked.connect(self._generate_schedule)
        layout.addWidget(self.generate_schedule_button)

        # Regular season controls
        self.remaining_label = QLabel()
        layout.addWidget(self.remaining_label)
        self.simulation_status_label = QLabel()
        self.simulation_status_label.setWordWrap(True)
        layout.addWidget(self.simulation_status_label)

        self.simulate_day_button = QPushButton("Simulate Day")
        self.simulate_day_button.clicked.connect(self._simulate_day)
        layout.addWidget(self.simulate_day_button)

        self.simulate_week_button = QPushButton("Simulate Week")
        self.simulate_week_button.clicked.connect(self._simulate_week)
        layout.addWidget(self.simulate_week_button)

        self.simulate_month_button = QPushButton("Simulate Month")
        self.simulate_month_button.clicked.connect(self._simulate_month)
        layout.addWidget(self.simulate_month_button)

        self.cancel_sim_button = QPushButton("Cancel Simulation")
        self.cancel_sim_button.setEnabled(False)
        self.cancel_sim_button.clicked.connect(self._request_cancel_simulation)
        layout.addWidget(self.cancel_sim_button)

        # Maintenance tool: repair/auto-fill lineups
        self.repair_lineups_button = QPushButton("Repair Lineups")
        self.repair_lineups_button.clicked.connect(self._repair_lineups)
        layout.addWidget(self.repair_lineups_button)

        self.simulate_phase_button = QPushButton("Simulate to Next Phase")
        self.simulate_phase_button.clicked.connect(self._simulate_to_next_phase)
        layout.addWidget(self.simulate_phase_button)

        self.next_button = QPushButton("Next Phase")
        self.next_button.clicked.connect(self._next_phase)
        layout.addWidget(self.next_button)

        self._sim_status_text: Optional[str] = None
        try:
            self._simStatusRequested.connect(self._apply_simulation_status)
        except Exception:
            # Fallback stubs do not expose Qt signal semantics
            pass
        self._set_simulation_status(None)
        self._update_ui()

    # ------------------------------------------------------------------
    # Draft helpers
    def _compute_draft_date(self, first_date: str | None) -> str | None:
        try:
            if not first_date:
                return None
            year = int(str(first_date).split("-")[0])
            import datetime as _dt
            d = _dt.date(year, 7, 1)
            # Tuesday is 1
            while d.weekday() != 1:
                d += _dt.timedelta(days=1)
            d += _dt.timedelta(days=14)
            return d.isoformat()
        except Exception:
            return None

    def _days_until_draft(self) -> int:
        """Return the number of remaining schedule days until Draft Day."""
        draft_date = getattr(self, "_draft_date", None)
        if not draft_date:
            return 0

        try:
            draft_year = int(str(draft_date).split("-")[0])
        except Exception:
            draft_year = None

        # If the draft was already completed for this year, no countdown.
        if draft_year is not None:
            try:
                if PROGRESS_FILE.exists():
                    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8") or "{}")
                    completed = set(progress.get("draft_completed_years", []))
                    if draft_year in completed:
                        return 0
            except Exception:
                pass

        dates = getattr(self.simulator, "dates", None)
        idx = getattr(self.simulator, "_index", 0)
        if dates:
            try:
                remaining = 0
                for offset, value in enumerate(dates[idx:], start=0):
                    if str(value) >= str(draft_date):
                        remaining = offset
                        break
                else:
                    remaining = 0
                return max(0, remaining)
            except Exception:
                pass

        # Calendar fallback if schedule context is unavailable.
        try:
            from datetime import date as _date

            dy, dm, dd = map(int, str(draft_date).split("-"))
            draft_dt = _date(dy, dm, dd)

            cur_str: str | None = None
            if dates and idx < len(dates):
                cur_str = str(dates[idx])
            if not cur_str:
                cur_str = get_current_sim_date()
            if cur_str:
                cy, cm, cd = map(int, str(cur_str).split("-"))
                current_dt = _date(cy, cm, cd)
                delta = (draft_dt - current_dt).days
                if delta > 0:
                    return delta
        except Exception:
            pass
        return 0

    def _on_draft_day(self, date_str: str) -> None:
        """Handle Draft Day and block further simulation until committed.

        On Draft Day, enter the Amateur Draft phase and open the Draft Console.
        If the user does not commit results or any error occurs (including
        console initialization issues), raise DraftRosterError to prevent the
        season from progressing past the draft. This ensures commissioners
        cannot simulate beyond Draft Day without completing the draft.
        """
        import json as _json
        # Determine current season year from date string
        try:
            year = int(str(date_str).split("-")[0])
        except Exception:
            # If we cannot parse the date, block progression conservatively
            raise DraftRosterError(["Unable to determine season year for Draft Day."], {})

        # Skip if already completed for this year
        progress = {}
        if PROGRESS_FILE.exists():
            try:
                progress = _json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            except Exception:
                progress = {}
        completed = set(progress.get("draft_completed_years", []))
        if year in completed:
            return

        # Enter Amateur Draft phase in the manager/UI
        try:
            self.manager.phase = SeasonPhase.AMATEUR_DRAFT
            self.manager.save()
            self._update_ui("Amateur Draft Day: paused for draft operations.")
        except Exception:
            # Even if UI update fails, still enforce blocking via exception
            pass

        # Open Draft Console and require commit before resuming
        try:
            dlg = DraftConsole(date_str, self)
            dlg.exec()
            summary = dict(getattr(dlg, "assignment_summary", {}) or {})
            failures = list(summary.get("failures") or [])
            # If no commit occurred, require it before resuming
            if not summary:
                failures = [
                    "Draft results must be committed before resuming the season."
                ]
            # Only hard failures block the season. Compliance issues are surfaced
            # as warnings but do not prevent marking the draft complete.
            if failures:
                raise DraftRosterError(failures, summary)

            # Mark draft completed for the year and return to regular season
            completed.add(year)
            progress["draft_completed_years"] = sorted(completed)
            try:
                PROGRESS_FILE.write_text(
                    _json.dumps(progress, indent=2), encoding="utf-8"
                )
            except Exception:
                # If persistence fails, block progression to avoid skipping the draft
                raise DraftRosterError(["Failed to persist draft completion."], summary)
            try:
                self.manager.phase = SeasonPhase.REGULAR_SEASON
                self.manager.save()
                self._update_ui("Draft committed. Returning to Regular Season.")
            except Exception:
                # Even if UI update fails, the draft is complete; continue
                pass
        except DraftRosterError:
            # Remain in draft phase when assignments are incomplete
            raise
        except Exception as exc:
            # Any error initializing or running the console should block
            # season progression to ensure the draft is not skipped.
            raise DraftRosterError([f"Draft Console error: {exc}"] , {})

    # ------------------------------------------------------------------
    # UI lifecycle
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        try:
            cur = get_current_sim_date()
            self.progressUpdated.emit(cur or "")
        except Exception:
            pass
        if self._active_future is not None and hasattr(self._active_future, "cancel"):
            try:
                self._active_future.cancel()
            except Exception:
                pass
        try:
            self.cancel_sim_button.setEnabled(False)
        except Exception:
            pass
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass
            self._executor = None
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _update_ui(self, note: str | None = None, *, bracket: object | None = None) -> None:
        """Refresh the label and notes for the current phase.

        Parameters
        ----------
        note:
            Optional note to display instead of the default phase message.
        bracket:
            Optional in-memory playoff bracket to reuse when refreshing the
            playoffs view to avoid stale disk reads after background updates.
        """
        phase_name = self.manager.phase.name.replace("_", " ").title()
        self.phase_label.setText(f"Current Phase: {phase_name}")
        # Update current date indicator from simulator schedule
        try:
            if self.simulator and getattr(self.simulator, "dates", None):
                if self.simulator._index < len(self.simulator.dates):
                    current_date = str(self.simulator.dates[self.simulator._index])
                elif self.simulator.dates:
                    current_date = str(self.simulator.dates[-1]) + " (complete)"
                else:
                    current_date = "N/A"
            else:
                current_date = "N/A"
        except Exception:
            current_date = "N/A"
        try:
            self.date_label.setText(f"Current Date: {current_date}")
        except Exception:
            pass
        if note is None:
            note = self.manager.handle_phase()
        self.notes_label.setText(note)

        is_preseason = self.manager.phase == SeasonPhase.PRESEASON
        is_regular = self.manager.phase == SeasonPhase.REGULAR_SEASON
        is_playoffs = self.manager.phase == SeasonPhase.PLAYOFFS
        is_draft = self.manager.phase == SeasonPhase.AMATEUR_DRAFT
        self.free_agency_button.setVisible(is_preseason)
        self.training_camp_button.setVisible(is_preseason)
        self.generate_schedule_button.setVisible(is_preseason)
        self.remaining_label.setVisible(is_regular or is_playoffs)
        self.simulate_day_button.setVisible(is_regular)
        self.simulate_week_button.setVisible(is_regular)
        self.simulate_month_button.setVisible(is_regular)
        self.simulate_phase_button.setVisible(is_regular or is_playoffs)
        self.repair_lineups_button.setVisible(is_regular)
        playoffs_bracket = bracket
        if is_regular:
            mid_remaining = self.simulator.remaining_days()
            # Draft milestone: only if not yet completed for the season
            try:
                draft_remaining = self._days_until_draft()  # type: ignore[attr-defined]
            except AttributeError:
                draft_remaining = 0
            total_remaining = self.simulator.remaining_schedule_days()
            if total_remaining > 0:
                if mid_remaining > 0:
                    label_text = f"Days until Midseason: {mid_remaining}"
                elif draft_remaining > 0:
                    label_text = f"Days until Draft: {draft_remaining}"
                else:
                    label_text = f"Days until Season End: {total_remaining}"
            else:
                label_text = "Regular season complete."
            self.remaining_label.setText(label_text)
            has_games = total_remaining > 0
            self.simulate_day_button.setEnabled(has_games)
            self.simulate_week_button.setEnabled(has_games)
            self.simulate_month_button.setEnabled(has_games)
            self.simulate_phase_button.setEnabled(has_games)
            if has_games:
                if mid_remaining > 0:
                    self.simulate_phase_button.setText("Simulate to Midseason")
                elif draft_remaining > 0:
                    self.simulate_phase_button.setText("Simulate to Draft")
                else:
                    self.simulate_phase_button.setText("Simulate to Playoffs")
            else:
                self.simulate_phase_button.setText("Simulate to Playoffs")
            season_done = self.simulator._index >= len(self.simulator.dates)
            self.next_button.setEnabled(season_done)
        elif is_preseason:
            self.free_agency_button.setEnabled(
                not self._preseason_done["free_agency"]
            )
            self.training_camp_button.setEnabled(
                self._preseason_done["free_agency"]
                and not self._preseason_done["training_camp"]
            )
            self.generate_schedule_button.setEnabled(
                self._preseason_done["training_camp"]
                and not self._preseason_done["schedule"]
            )
            self.simulate_phase_button.setEnabled(False)
            self.next_button.setEnabled(self._preseason_done["schedule"])
        elif is_playoffs:
            # If a completed bracket already exists (e.g., simulated via Playoffs Viewer),
            # recognize it and flip the playoffs-done flag so the UI advances without
            # requiring another simulation pass here. If no explicit champion is stored
            # but the championship round has winners decided, infer and persist it.
            if not self._playoffs_done:
                try:
                    from playbalance.playoffs import load_bracket as _lb, save_bracket as _sb
                    b = playoffs_bracket or _lb()
                    playoffs_bracket = b
                    def _is_final_round(name: str) -> bool:
                        tokens = [t.lower() for t in str(name or "").replace("-", " ").replace("_", " ").split() if t]
                        final_tokens = {"ws", "world", "worlds", "final", "finals", "championship"}
                        return any(t in final_tokens for t in tokens)
                    def _final_round(br) -> object | None:
                        rounds = list(getattr(br, "rounds", []) or [])
                        finals = [r for r in rounds if _is_final_round(getattr(r, "name", ""))]
                        if finals:
                            return finals[-1]
                        return rounds[-1] if rounds else None
                    if b:
                        if getattr(b, "champion", None):
                            self._playoffs_done = True
                            self._save_progress()
                        else:
                            fr = _final_round(b)
                            matchups = list(getattr(fr, "matchups", []) or []) if fr else []
                            if matchups and all(getattr(m, "winner", None) for m in matchups):
                                champ = getattr(matchups[0], "winner", None)
                                if champ:
                                    try:
                                        # Persist inferred champion for consistency across windows
                                        b.champion = champ
                                        m = matchups[0]
                                        b.runner_up = m.low.team_id if champ == m.high.team_id else m.high.team_id
                                        _sb(b)
                                    except Exception:
                                        pass
                                    self._playoffs_done = True
                                    self._save_progress()
                except Exception:
                    pass
            if self._playoffs_done:
                self.remaining_label.setText("Playoffs complete.")
            else:
                self.remaining_label.setText("Playoffs underway; simulate to continue.")
            self.simulate_phase_button.setText("Simulate Playoffs")
            self.simulate_phase_button.setEnabled(not self._playoffs_done)
            self.next_button.setEnabled(self._playoffs_done)
        elif is_draft:
            # During draft, hide simulation controls; user manages the draft via Draft Console
            self.remaining_label.setVisible(False)
            self.simulate_phase_button.setVisible(False)
            self.simulate_day_button.setVisible(False)
            self.simulate_week_button.setVisible(False)
            self.simulate_month_button.setVisible(False)
            self.repair_lineups_button.setVisible(False)
            self.next_button.setEnabled(False)
        else:
            self.remaining_label.setVisible(False)
            self.simulate_phase_button.setVisible(False)
            self.next_button.setEnabled(True)
        # Timeline reflects updated status after any UI refresh.
        self._refresh_timeline(bracket=playoffs_bracket)

    def _set_simulation_status(self, text: str | None) -> None:
        """Show or hide the simulation status label."""

        if QThread is None:
            self._apply_simulation_status(text)
            return
        try:
            gui_thread = self.thread()
            current_thread = QThread.currentThread()
        except Exception:
            gui_thread = None
            current_thread = None
        if (
            gui_thread is not None
            and current_thread is not None
            and gui_thread != current_thread
        ):
            try:
                self._simStatusRequested.emit(text)
            except Exception:
                pass
            return
        self._apply_simulation_status(text)

    def _apply_simulation_status(self, text: str | None) -> None:
        """Apply the simulation status label update on the GUI thread."""

        label = getattr(self, "simulation_status_label", None)
        if label is None:
            return
        if text:
            if self._sim_status_text == text:
                return
            try:
                label.setText(text)
                label.setVisible(True)
            except RuntimeError:
                return
            self._sim_status_text = text
        else:
            self._sim_status_text = None
            try:
                label.clear()
                label.setVisible(False)
            except RuntimeError:
                pass

    def _consume_rollover_note(self) -> str | None:
        """Return and clear any pending rollover summary message."""
        result = getattr(self.manager, "rollover_result", None)
        if not result:
            return None
        status = getattr(result, "status", "")
        message: str | None = None
        if status == "archived":
            season_id = getattr(result, "season_id", "season")
            message = f"Season {season_id} archived; next season prepared."
            if self._show_toast:
                self._show_toast("success", message)
        elif status == "error":
            reason = getattr(result, "reason", "unknown error")
            message = f"Season rollover failed: {reason}"
            if self._show_toast:
                self._show_toast("error", message)
        elif status == "skipped":
            note = getattr(result, "reason", None)
            if note:
                message = note
                if self._show_toast:
                    self._show_toast("info", message)
        self.manager.rollover_result = None
        return message

    @staticmethod
    def _format_simulation_progress(label: str, done: int, total: int) -> str:
        """Return a human-friendly progress string for ``done`` of ``total`` days."""

        total = max(total, 1)
        done = max(0, min(done, total))
        percent = min(100.0, (done / total) * 100.0)
        remaining = max(total - done, 0)
        parts = [
            f"Simulating {label.lower()}",
            f"{done}/{total} days",
            f"{percent:.0f}% complete",
        ]
        if remaining > 0:
            parts.append(f"{remaining} days remaining")
        return " - ".join(parts)

    def _refresh_timeline(self, *, bracket: object | None = None) -> None:
        """Populate the season timeline list with milestone statuses."""
        timeline = getattr(self, "timeline", None)
        if timeline is None:
            return
        try:
            timeline.clear()
        except Exception:
            return

        status_labels = {
            "done": "Done",
            "current": "In Progress",
            "pending": "Upcoming",
        }
        status_colors = {
            "done": QColor("#2e7d32"),
            "current": QColor("#1565c0"),
            "pending": QColor("#6c757d"),
        }

        def resolve_status(completed: bool, active: bool) -> str:
            if completed:
                return "done"
            if active:
                return "current"
            return "pending"

        def add_event(title: str, status: str, detail: str | None = None) -> None:
            label = status_labels.get(status, status.title())
            text = f"{title} — {label}"
            item = QListWidgetItem(text)
            if detail:
                try:
                    item.setToolTip(detail)
                except Exception:
                    pass
            color = status_colors.get(status)
            if color is not None:
                try:
                    item.setForeground(color)
                except Exception:
                    pass
            if status == "current":
                try:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                except Exception:
                    pass
            try:
                timeline.addItem(item)
            except Exception:
                pass

        phase = self.manager.phase
        schedule_dates = list(getattr(self.simulator, "dates", []) or [])
        current_index = int(getattr(self.simulator, "_index", 0) or 0)
        total_days = len(schedule_dates)
        opening_day = str(schedule_dates[0]) if schedule_dates else None
        mid_index = getattr(self.simulator, "_mid", total_days // 2)
        mid_date = (
            str(schedule_dates[mid_index])
            if schedule_dates and 0 <= mid_index < total_days
            else None
        )
        draft_date = self._draft_date

        progress_data: dict[str, object] = {}
        try:
            if PROGRESS_FILE.exists():
                progress_data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            progress_data = {}
        draft_completed_years = set(
            progress_data.get("draft_completed_years", []) or []
        )

        current_date = get_current_sim_date()

        preseason_order = [
            ("Preseason • Free Agency", "free_agency", "List unsigned players and review bids."),
            ("Preseason • Training Camp", "training_camp", "Run training camp to mark players ready."),
            ("Preseason • Generate Schedule", "schedule", "Create the regular-season schedule."),
        ]
        prerequisites_complete = True
        for title, key, detail in preseason_order:
            done = bool(self._preseason_done.get(key))
            active = (
                phase == SeasonPhase.PRESEASON
                and not done
                and prerequisites_complete
            )
            add_event(title, resolve_status(done, active), detail)
            prerequisites_complete = prerequisites_complete and done

        if opening_day:
            opening_done = current_index > 0 or phase in {
                SeasonPhase.REGULAR_SEASON,
                SeasonPhase.PLAYOFFS,
                SeasonPhase.AMATEUR_DRAFT,
                SeasonPhase.OFFSEASON,
            }
            opening_active = (
                phase == SeasonPhase.PRESEASON
                and self._preseason_done.get("schedule")
                and not opening_done
            )
            add_event(
                "Regular Season • Opening Day",
                resolve_status(opening_done, opening_active),
                f"Scheduled for {opening_day}",
            )

        if mid_date:
            mid_done = current_index > mid_index or phase in {
                SeasonPhase.PLAYOFFS,
                SeasonPhase.AMATEUR_DRAFT,
                SeasonPhase.OFFSEASON,
            }
            mid_active = (
                phase == SeasonPhase.REGULAR_SEASON
                and current_index <= mid_index
                and not mid_done
            )
            add_event(
                "Regular Season • Midseason Break",
                resolve_status(mid_done, mid_active),
                f"Target date {mid_date}",
            )

        if draft_date:
            detail_parts = [f"Draft Day: {draft_date}"]
            draft_year = None
            try:
                draft_year = int(str(draft_date).split("-")[0])
            except Exception:
                draft_year = None
            draft_done = draft_year in draft_completed_years if draft_year else False
            try:
                days_until = self._days_until_draft()
            except Exception:
                days_until = None
            if isinstance(days_until, int):
                if days_until > 0:
                    detail_parts.append(f"{days_until} days remaining")
                elif days_until == 0:
                    detail_parts.append("Draft is scheduled for today")
                else:
                    detail_parts.append(f"{abs(days_until)} days past target")
            if current_date:
                detail_parts.append(f"Current date: {current_date}")
            draft_active = (
                not draft_done
                and (
                    phase == SeasonPhase.AMATEUR_DRAFT
                    or (
                        phase == SeasonPhase.REGULAR_SEASON
                        and isinstance(days_until, int)
                        and days_until <= 0
                    )
                )
            )
            add_event(
                "Regular Season • Draft Day",
                resolve_status(draft_done, draft_active),
                " • ".join(detail_parts),
            )

        playoffs_done = bool(self._playoffs_done)
        playoffs_active = phase == SeasonPhase.PLAYOFFS and not playoffs_done
        add_event(
            "Postseason • Playoffs",
            resolve_status(playoffs_done, playoffs_active),
            "Simulate rounds and record bracket outcomes.",
        )

        champion = None
        runner_up = None
        playoff_bracket = bracket
        try:
            from playbalance.playoffs import load_bracket as _load_bracket

            if playoff_bracket is None:
                playoff_bracket = _load_bracket()
            if playoff_bracket is not None:
                champion = getattr(playoff_bracket, "champion", None)
                runner_up = getattr(playoff_bracket, "runner_up", None)
        except Exception:
            champion = None

        if champion or playoffs_done or playoffs_active:
            if champion:
                detail = (
                    f"Champion: {champion}"
                    + (f" • Runner-up: {runner_up}" if runner_up else "")
                )
            elif playoffs_done:
                detail = "Awaiting championship record."
            else:
                detail = "Final series underway."
            add_event(
                "Postseason • Championship",
                resolve_status(bool(champion), playoffs_active and not champion),
                detail,
            )

        if timeline.count() == 0:
            add_event("Timeline data unavailable", "pending")

    def _next_phase(self) -> None:
        """Advance to the next phase and update the display."""
        if self.manager.phase == SeasonPhase.OFFSEASON:
            players = getattr(self.manager, "players", {})
            retired = age_and_retire(players)
            self.notes_label.setText(f"Retired Players: {len(retired)}")
            season_manager.TRADE_DEADLINE = date(date.today().year + 1, 7, 31)
            self.manager.phase = SeasonPhase.PRESEASON
            self.manager.save()
            self._preseason_done = {
                "free_agency": False,
                "training_camp": False,
                "schedule": False,
            }
            self._playoffs_done = False
            if self._simulate_game is not None:
                self.simulator = SeasonSimulator([], self._simulate_game)
            else:
                self.simulator = SeasonSimulator([])
            note = f"Retired Players: {len(retired)}"
        elif self.manager.phase == SeasonPhase.REGULAR_SEASON:
            # If the regular season is complete, skip the Amateur Draft phase
            # and proceed directly to the Playoffs. The draft is handled as an
            # in-season milestone (Draft Day). If it was missed or already
            # completed, it should not block postseason advancement here.
            season_done = self.simulator._index >= len(self.simulator.dates)
            if season_done:
                self.manager.phase = SeasonPhase.PLAYOFFS
                self.manager.save()
                self._playoffs_done = False
                # Merge daily shards now that regular season is complete.
                try:  # pragma: no cover - best effort merge
                    from utils.stats_persistence import merge_daily_history as _merge
                    _merge()
                except Exception:
                    pass
                # Ensure a playoff bracket exists when entering playoffs
                try:
                    self._ensure_playoff_bracket()
                except Exception:
                    pass
                note = None
            else:
                self.manager.advance_phase()
                if self.manager.phase == SeasonPhase.PLAYOFFS:
                    self._playoffs_done = False
                    # If transitioning into playoffs, ensure a bracket exists
                    try:
                        self._ensure_playoff_bracket()
                    except Exception:
                        pass
                note = None
        else:
            previous_phase = self.manager.phase
            self.manager.advance_phase()
            if self.manager.phase == SeasonPhase.PLAYOFFS:
                self._playoffs_done = False
                try:
                    self._ensure_playoff_bracket()
                except Exception:
                    pass
            if previous_phase == SeasonPhase.PLAYOFFS:
                note = self._consume_rollover_note()
            else:
                note = None
        log_news_event(
            f"Season advanced to {self.manager.phase.name.replace('_', ' ').title()}"
        )
        self._save_progress()
        self._update_ui(note)

    # ------------------------------------------------------------------
    # Preseason actions
    # ------------------------------------------------------------------
    def _show_free_agents(self) -> None:
        """Display a simple list of unsigned players."""
        players = getattr(self.manager, "players", {})
        teams = getattr(self.manager, "teams", [])
        agents = list_unsigned_players(players, teams)
        if agents:
            names = ", ".join(f"{p.first_name} {p.last_name}" for p in agents)
            self.notes_label.setText(f"Unsigned Players: {names}")
            log_news_event(
                f"Listed unsigned players: {len(agents)} available"
            )
        else:
            self.notes_label.setText("No unsigned players available.")
            log_news_event("No unsigned players available")

        self.free_agency_button.setEnabled(False)
        self._preseason_done["free_agency"] = True
        message = (
            f"Unsigned Players: {names}" if agents else "No unsigned players available."
        )
        self._save_progress()
        self._update_ui(message)

    def _run_training_camp(self) -> None:
        """Run the training camp and mark players as ready."""
        players = getattr(self.manager, "players", {})
        run_training_camp(players.values())
        self.notes_label.setText("Training camp completed. Players marked ready.")
        log_news_event("Training camp completed; players marked ready")
        self.training_camp_button.setEnabled(False)
        self._preseason_done["training_camp"] = True
        self._save_progress()
        self._update_ui("Training camp completed. Players marked ready.")

    def _generate_schedule(self) -> None:
        """Create a full MLB-style schedule for the league."""
        teams = [
            getattr(t, "abbreviation", str(t))
            for t in getattr(self.manager, "teams", [])
        ]
        if not teams and TEAMS_FILE.exists():
            with TEAMS_FILE.open(newline="") as fh:
                reader = csv.DictReader(fh)
                teams = [row["abbreviation"] for row in reader]
        if not teams:
            self._update_ui("No teams available to generate schedule.")
            return

        start = date(date.today().year, 4, 1)
        schedule = generate_mlb_schedule(teams, start)
        save_schedule(schedule, SCHEDULE_FILE)
        try:
            from playbalance.season_context import SeasonContext as _SeasonContext

            if schedule:
                first_date = str(schedule[0].get("date") or "").strip()
                if first_date:
                    try:
                        year = int(first_date.split("-")[0])
                    except Exception:
                        year = None
                    ctx = _SeasonContext.load()
                    ctx.ensure_current_season(league_year=year, started_on=first_date)
        except Exception:
            pass
        if self._simulate_game is not None:
            self.simulator = SeasonSimulator(
                schedule, self._simulate_game, after_game=self._record_game
            )
        else:
            self.simulator = SeasonSimulator(
                schedule, after_game=self._record_game
            )
        message = f"Schedule generated with {len(schedule)} games."
        log_news_event(f"Generated regular season schedule with {len(schedule)} games")
        self.generate_schedule_button.setEnabled(False)
        self._preseason_done["schedule"] = True
        self._save_progress()
        self._update_ui(message)

    # ------------------------------------------------------------------
    # Regular season actions
    # ------------------------------------------------------------------
    def _simulate_day(self) -> None:
        """Trigger simulation for a single schedule day."""
        if self.simulator.remaining_schedule_days() <= 0:
            return
        # Ensure schedule uses valid team IDs before simulating
        if not self._ensure_valid_schedule_teams():
            return
        # Validate lineups for all teams; stop if any are invalid
        issues = self._validate_all_team_lineups()
        if issues:
            QMessageBox.warning(self, "Missing Lineup or Pitching", "\n".join(issues))
            return
        try:
            self.simulator.simulate_next_day()
        except DraftRosterError as exc:
            message = str(exc) or "Draft assignments remain incomplete."
            failures = getattr(exc, 'failures', None)
            if failures:
                message += "\n\n" + "\n".join(failures)
            QMessageBox.warning(self, "Draft Assignments Incomplete", message)
            return
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(
                self, "Missing Lineup or Pitching", str(e)
            )
            return
        mid_remaining = self.simulator.remaining_days()
        total_remaining = self.simulator.remaining_schedule_days()
        if total_remaining > 0:
            if mid_remaining > 0:
                self.remaining_label.setText(
                    f"Days until Midseason: {mid_remaining}"
                )
                remaining_msg = f"{mid_remaining} days until Midseason"
            else:
                self.remaining_label.setText(
                    f"Days until Season End: {total_remaining}"
                )
                remaining_msg = f"{total_remaining} days until Season End"
        else:
            self.remaining_label.setText("Regular season complete.")
            remaining_msg = "regular season complete"
        message = f"Simulated a regular season day; {remaining_msg}"
        if self._pb_cfg is not None:
            try:
                stats = pb_simulate_day(self._pb_cfg, self._pb_benchmarks)
                pa = stats.pa or 1
                k_pct = stats.k / pa
                bb_pct = stats.bb / pa
                message += f" (K% {k_pct:.3f}, BB% {bb_pct:.3f})"
            except Exception:  # pragma: no cover - best effort
                pass
        self.notes_label.setText(message)
        # Log daily recap for the date just simulated
        try:
            if self.simulator._index > 0 and self.simulator._index - 1 < len(self.simulator.dates):
                date_just_played = str(self.simulator.dates[self.simulator._index - 1])
                self._log_daily_recap_for_date(date_just_played)
        except Exception:
            pass
        log_news_event(message, category="progress")
        self._save_progress()
        self._update_ui(message)
        # Always merge daily shards into canonical history after any simulation.
        try:  # pragma: no cover - best effort merge
            from utils.stats_persistence import merge_daily_history as _merge
            _merge()
        except Exception:
            pass
        # Clear loader caches so other windows see fresh stats immediately
        try:
            from utils.player_loader import load_players_from_csv as _lp
            _lp.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            from utils.roster_loader import load_roster as _lr
            _lr.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass

    def _simulate_span(self, days: int, label: str) -> None:
        self._simulate_span_async(days, label)

    def _request_cancel_simulation(self) -> None:
        """Attempt to cancel the currently running background simulation."""
        if self._active_future is None:
            return
        self._cancel_requested = True
        self._set_simulation_status("Cancelling simulation in progress...")
        try:
            self.cancel_sim_button.setEnabled(False)
        except Exception:
            pass
        if hasattr(self._active_future, "cancel"):
            try:
                self._active_future.cancel()
            except Exception:
                pass
        if self._show_toast:
            self._show_toast("info", "Attempting to cancel the current simulation...")

    def _simulate_span_async(self, days: int, label: str) -> None:
        if self.simulator.remaining_schedule_days() <= 0:
            return
        if not self._ensure_valid_schedule_teams():
            return
        issues = self._validate_all_team_lineups()
        if issues:
            QMessageBox.warning(self, "Missing Lineup or Pitching", "\n".join(issues))
            return
        if self._active_future is not None:
            QMessageBox.information(
                self,
                "Simulation Running",
                "A simulation is already in progress. Please wait for it to finish.",
            )
            return

        start = self.simulator._index
        end = min(start + days, len(self.simulator.dates))
        upcoming = list(self.simulator.dates[start:end])
        self._cancel_requested = False
        total_goal = len(upcoming)
        if total_goal <= 0:
            self._set_simulation_status(
                f"No games available for the selected {label.lower()} span."
            )
            return

        self._set_sim_buttons_enabled(False)
        try:
            self.cancel_sim_button.setEnabled(True)
        except Exception:
            pass

        def publish_progress(done: int, *, cancelling: bool = False) -> None:
            text = self._format_simulation_progress(label, done, total_goal)
            if cancelling:
                text = f"{text} - cancelling..."

            self._set_simulation_status(text)

        publish_progress(0)

        if self._show_toast:
            self._show_toast("info", f"Simulating {label.lower()} in background...")

        def worker() -> Tuple[str, dict[str, Any]]:
            warning: Optional[Tuple[str, str]] = None
            simulated_days = 0
            try:
                while (
                    simulated_days < days
                    and self.simulator.remaining_schedule_days() > 0
                ):
                    try:
                        self.simulator.simulate_next_day()
                    except DraftRosterError as exc:
                        message = str(exc) or "Draft assignments remain incomplete."
                        failures = getattr(exc, "failures", None)
                        if failures:
                            message += "\n\n" + "\n".join(failures)
                        warning = ("draft", message)
                        break
                    except (FileNotFoundError, ValueError) as err:
                        warning = ("lineup", str(err))
                        break
                    simulated_days += 1
                    publish_progress(simulated_days, cancelling=self._cancel_requested)
                    if self._cancel_requested:
                        break
                was_cancelled = bool(self._cancel_requested and simulated_days < total_goal)
                publish_progress(simulated_days, cancelling=was_cancelled)
                return (
                    "success",
                    {
                        "simulated_days": simulated_days,
                        "warning": warning,
                        "was_cancelled": was_cancelled,
                        "upcoming": upcoming,
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive
                return ("error", str(exc))

        future = self._run_async(worker)
        self._active_future = future

        def handle_result(fut) -> None:
            try:
                result = fut.result()
            except Exception as exc:  # pragma: no cover - defensive
                result = ("error", str(exc))

            def finish() -> None:
                self._active_future = None
                self._set_sim_buttons_enabled(True)
                try:
                    self.cancel_sim_button.setEnabled(False)
                except Exception:
                    pass
                kind, payload = result
                if kind == "error":
                    error_text = str(payload)
                    self._set_simulation_status(f"Simulation failed: {error_text}")
                    QMessageBox.warning(self, "Simulation Failed", error_text)
                    if self._show_toast:
                        self._show_toast("error", error_text)
                    self._update_ui()
                    return
                warning = payload.get("warning")
                if warning is not None:
                    QMessageBox.warning(self, "Simulation Warning", warning[1])
                was_cancelled = payload.get("was_cancelled", False)
                message = self._finalize_span(
                    payload.get("simulated_days", 0),
                    days,
                    label,
                    payload.get("upcoming", []),
                    was_cancelled,
                )
                if self._show_toast:
                    if warning is not None:
                        toast_kind = "error"
                    elif was_cancelled:
                        toast_kind = "info"
                    else:
                        toast_kind = "success"
                    self._show_toast(toast_kind, message)

            QTimer.singleShot(0, finish)

        if hasattr(future, "add_done_callback"):
            future.add_done_callback(handle_result)
            if self._register_cleanup and hasattr(future, "cancel"):
                self._register_cleanup(lambda fut=future: fut.cancel())
        else:  # pragma: no cover - fallback for synchronous workers
            handle_result(type("_Immediate", (), {"result": lambda self: future})())

    def _set_sim_buttons_enabled(self, enabled: bool) -> None:
        for btn in (
            self.simulate_day_button,
            self.simulate_week_button,
            self.simulate_month_button,
            self.simulate_phase_button,
        ):
            try:
                btn.setEnabled(enabled)
            except Exception:
                pass

    def _finalize_span(
        self,
        simulated_days: int,
        days: int,
        label: str,
        upcoming: list,
        was_cancelled: bool,
    ) -> str:
        total_goal = len(upcoming) or days
        total_goal = max(total_goal, 1)
        mid_remaining = self.simulator.remaining_days()
        draft_remaining = self._days_until_draft()
        total_remaining = self.simulator.remaining_schedule_days()
        if total_remaining > 0:
            if mid_remaining > 0:
                self.remaining_label.setText(
                    f"Days until Midseason: {mid_remaining}"
                )
                remaining_msg = f"{mid_remaining} days until Midseason"
            elif draft_remaining > 0:
                self.remaining_label.setText(
                    f"Days until Draft: {draft_remaining}"
                )
                remaining_msg = f"{draft_remaining} days until Draft"
            else:
                self.remaining_label.setText(
                    f"Days until Season End: {total_remaining}"
                )
                remaining_msg = f"{total_remaining} days until Season End"
        else:
            self.remaining_label.setText("Regular season complete.")
            remaining_msg = "regular season complete"

        if was_cancelled:
            if simulated_days <= 0:
                progress_note = "no days completed during the run"
            elif simulated_days == 1:
                progress_note = "completed 1 day this run"
            else:
                progress_note = f"completed {simulated_days} days this run"
            message = (
                f"Simulation cancelled during {label.lower()}; "
                f"{progress_note}, {remaining_msg}"
            )
        else:
            message = f"Simulated {label.lower()}; {remaining_msg}"

        if not was_cancelled and self._pb_cfg is not None:
            try:
                if days >= 30:
                    stats = pb_simulate_month(self._pb_cfg, self._pb_benchmarks)
                elif days >= 7:
                    stats = pb_simulate_week(self._pb_cfg, self._pb_benchmarks)
                else:
                    stats = pb_simulate_day(self._pb_cfg, self._pb_benchmarks)
                pa = stats.pa or 1
                k_pct = stats.k / pa
                bb_pct = stats.bb / pa
                message += f" (K% {k_pct:.3f}, BB% {bb_pct:.3f})"
            except Exception:  # pragma: no cover - best effort
                pass

        self.notes_label.setText(message)
        percent = min(100.0, (simulated_days / total_goal) * 100.0)
        status_suffix = f"{simulated_days}/{total_goal} days ({percent:.0f}% complete)"
        self._set_simulation_status(f"{message} - {status_suffix}")
        try:
            dates_covered = [str(d) for d in upcoming[:simulated_days]]
            for d in dates_covered:
                self._log_daily_recap_for_date(d)
        except Exception:
            pass

        log_news_event(message, category="progress")
        self._save_progress()
        self._update_ui(message)

        try:  # pragma: no cover - best effort merge
            from utils.stats_persistence import merge_daily_history as _merge

            _merge()
        except Exception:
            pass
        try:
            from utils.player_loader import load_players_from_csv as _lp

            _lp.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            from utils.roster_loader import load_roster as _lr

            _lr.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass

        self._cancel_requested = False
        return message

    def _log_daily_recap_for_date(self, date_str: str) -> None:
        """Compose and append a daily recap for games on ``date_str``."""
        try:
            games = [g for g in self.simulator.schedule if str(g.get("date", "")) == str(date_str)]
        except Exception:
            games = []
        if not games:
            return
        played = [g for g in games if g.get("result")]
        if not played:
            return
        # Compute one-run and extras counts and build short examples
        one_run = 0
        extras = 0
        examples: list[str] = []
        for g in played:
            res = str(g.get("result") or "")
            if "-" in res:
                try:
                    hs, as_ = res.split("-", 1)
                    hs_i, as_i = int(hs), int(as_)
                    if abs(hs_i - as_i) == 1:
                        one_run += 1
                except Exception:
                    pass
            meta = g.get("extra") or {}
            if isinstance(meta, dict) and meta.get("extra_innings"):
                extras += 1
            # Add up to 3 examples
            if len(examples) < 3:
                examples.append(f"{g.get('away','')} at {g.get('home','')} â€” {res}")
        msg = (
            f"Daily Recap {date_str}: {len(played)} games; "
            f"{one_run} one-run; {extras} extras. "
            + "; ".join(examples)
        )
        log_news_event(msg, category="game_recap")

    def _simulate_to_next_phase(self) -> None:
        """Simulate games until the current phase can advance."""
        if self.manager.phase == SeasonPhase.REGULAR_SEASON:
            mid_remaining = self.simulator.remaining_days()
            if mid_remaining > 0:
                self._simulate_span(mid_remaining, "Midseason")
                return
            draft_remaining = self._days_until_draft()
            if draft_remaining > 0:
                self._simulate_span(draft_remaining, "Draft")
                return
            total_remaining = self.simulator.remaining_schedule_days()
            if total_remaining <= 0:
                return
            self._simulate_span(total_remaining, "Regular Season")
        elif self.manager.phase == SeasonPhase.PLAYOFFS:
            self._simulate_playoffs()

    def _simulate_week(self) -> None:
        """Simulate the next seven days or until the break."""
        self._simulate_span(7, "Week")

    def _simulate_month(self) -> None:
        """Simulate the next thirty days or until the break."""
        self._simulate_span(30, "Month")


    def _simulate_playoffs(self) -> None:
        """Simulate the postseason bracket with background support."""
        if self._playoffs_done:
            self._update_ui("Playoffs complete.")
            return
        if self._run_async is None:
            self._simulate_playoffs_sync()
        else:
            self._simulate_playoffs_async()

    def _simulate_playoffs_sync(self) -> None:
        self._set_playoff_controls_enabled(False)
        self._set_simulation_status("Simulating playoffs...")
        result = self._playoffs_workflow()
        self._handle_playoffs_result(result)

    def _simulate_playoffs_async(self) -> None:
        if self._active_future is not None:
            QMessageBox.information(
                self,
                "Simulation Running",
                "A simulation is already in progress. Please wait for it to finish.",
            )
            return
        self._set_playoff_controls_enabled(False)
        self._set_simulation_status("Simulating playoffs...")
        if self._show_toast:
            self._show_toast("info", "Simulating playoffs in background...")

        def worker() -> dict[str, Any]:
            return self._playoffs_workflow()

        future = self._run_async(worker)
        self._active_future = future

        def handle_result(fut) -> None:
            try:
                result = fut.result()
            except Exception as exc:  # defensive
                result = {"status": "error", "message": str(exc), "playoffs_done": False}

            def finish() -> None:
                self._active_future = None
                self._handle_playoffs_result(result)

            QTimer.singleShot(0, finish)

        if hasattr(future, "add_done_callback"):
            future.add_done_callback(handle_result)
            if self._register_cleanup and hasattr(future, "cancel"):
                self._register_cleanup(lambda fut=future: fut.cancel())
        else:
            handle_result(type("_Immediate", (), {"result": lambda self: future})())

    def _playoffs_workflow(self) -> dict[str, Any]:
        from playbalance.playoffs_config import load_playoffs_config
        from playbalance.playoffs import (
            load_bracket,
            save_bracket,
            generate_bracket,
            simulate_playoffs as run_playoffs,
        )
        from utils.team_loader import load_teams

        try:
            bracket = load_bracket()
        except Exception as exc:
            return {"status": "error", "message": f"Failed loading bracket: {exc}", "playoffs_done": False}

        if bracket and getattr(bracket, "champion", None):
            return {
                "status": "already_complete",
                "message": f"Playoffs already completed; champion: {bracket.champion}",
                "playoffs_done": True,
                "bracket": bracket,
            }

        if bracket is None:
            try:
                teams = load_teams()
            except Exception:
                teams = []
            cfg = load_playoffs_config()
            try:
                bracket = generate_bracket(self._standings, teams, cfg)
            except NotImplementedError:
                return {
                    "status": "engine_missing",
                    "message": "Playoffs engine unavailable; marking playoffs complete.",
                    "playoffs_done": True,
                }
            except Exception:
                return {
                    "status": "placeholder_complete",
                    "message": "Simulated playoffs; championship decided.",
                    "playoffs_done": True,
                }
            try:
                rounds = list(getattr(bracket, "rounds", []) or [])
                has_games = any(getattr(r, "matchups", None) for r in rounds)
            except Exception:
                has_games = False
            if not has_games:
                return {
                    "status": "placeholder_complete",
                    "message": "Simulated playoffs; championship decided.",
                    "playoffs_done": True,
                    "bracket": bracket,
                }

        def _persist(br):
            try:
                save_bracket(br)
            except Exception:
                pass

        try:
            bracket = run_playoffs(bracket, persist_cb=_persist)
        except NotImplementedError:
            return {
                "status": "engine_missing",
                "message": "Playoffs engine not available; cannot simulate.",
                "playoffs_done": False,
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Playoffs simulation encountered an error: {exc}",
                "playoffs_done": False,
            }

        champion = getattr(bracket, "champion", None)
        if champion:
            series_result = self._compute_series_result(bracket)
            return {
                "status": "completed",
                "message": f"Simulated playoffs; champion: {champion}",
                "playoffs_done": True,
                "bracket": bracket,
                "series_result": series_result,
            }

        return {
            "status": "placeholder_complete",
            "message": "Simulated playoffs; championship decided.",
            "playoffs_done": True,
            "bracket": bracket,
        }

    def _handle_playoffs_result(self, result: dict[str, Any]) -> None:
        status = result.get("status", "error")
        message = result.get("message", "")
        playoffs_done = bool(result.get("playoffs_done"))
        bracket = result.get("bracket")
        series_result = result.get("series_result", "")

        if playoffs_done:
            self._playoffs_done = True
            self._save_progress()

        if status == "error":
            QMessageBox.warning(self, "Playoffs Simulation", message)
            self._set_playoff_controls_enabled(True)
            self.next_button.setEnabled(self._playoffs_done)
            self._set_simulation_status(f"Playoffs simulation failed: {message}")
            if self._show_toast:
                self._show_toast("error", message)
            self._update_ui(message, bracket=bracket)
            return

        if status == "engine_missing":
            QMessageBox.information(self, "Playoffs Simulation", message)
            self._set_playoff_controls_enabled(False)
            self.next_button.setEnabled(True)
            log_news_event(message)
            self._set_simulation_status(message)
            if self._show_toast:
                self._show_toast("info", message)
            self._update_ui(message, bracket=bracket)
            return

        if status == "already_complete":
            self._set_playoff_controls_enabled(False)
            self.next_button.setEnabled(True)
            log_news_event(message)
            self._set_simulation_status(message)
            if self._show_toast:
                self._show_toast("success", message)
            self._update_ui(message, bracket=bracket)
            return

        if bracket is not None:
            try:
                from playbalance.playoffs import save_bracket as _save_bracket
                _save_bracket(bracket)
            except Exception:
                pass

        if status == "completed" and bracket is not None:
            self._write_champions_record(bracket, series_result)

        self._set_playoff_controls_enabled(False)
        self.next_button.setEnabled(True)
        log_news_event(message)
        if self._show_toast:
            self._show_toast("success", message)
        self._set_simulation_status(message)
        self._update_ui(message, bracket=bracket)

    def _set_playoff_controls_enabled(self, enabled: bool) -> None:
        try:
            self.simulate_phase_button.setEnabled(enabled)
        except Exception:
            pass
        if not enabled:
            try:
                self.next_button.setEnabled(False)
            except Exception:
                pass

    def _write_champions_record(self, bracket, series_result: str) -> None:
        try:
            import csv

            champions = DATA_DIR / "champions.csv"
            champions.parent.mkdir(parents=True, exist_ok=True)
            write_header = not champions.exists()
            with champions.open("a", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                if write_header:
                    writer.writerow(["year", "champion", "runner_up", "series_result"])
                writer.writerow([
                    getattr(bracket, "year", ""),
                    bracket.champion or "",
                    getattr(bracket, "runner_up", "") or "",
                    series_result,
                ])
        except Exception:
            pass

    def _compute_series_result(self, bracket) -> str:
        try:
            ws_round = next((r for r in bracket.rounds if r.name in {"WS", "Final"}), None)
            if not ws_round or not ws_round.matchups:
                return ""
            matchup = ws_round.matchups[0]
            champ = bracket.champion
            wins_c = 0
            wins_o = 0
            for game in getattr(matchup, "games", []):
                res = str(getattr(game, "result", "") or "")
                if "-" not in res:
                    continue
                try:
                    h, a = map(int, res.split("-", 1))
                except Exception:
                    continue
                if h > a:
                    winner = getattr(game, "home", "")
                elif a > h:
                    winner = getattr(game, "away", "")
                else:
                    continue
                if winner == champ:
                    wins_c += 1
                else:
                    wins_o += 1
            return f"{wins_c}-{wins_o}" if (wins_c or wins_o) else ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _record_game(self, game: dict[str, str]) -> None:
        """Persist league data after a single game.

        The season simulator invokes this callback after each scheduled game is
        played.  It marks the game as completed, rewrites the schedule file and
        dumps current team standings and player statistics to JSON files.  The
        files are intentionally simple so other parts of the application can
        load them without needing complex formats.
        """

        game["played"] = "1"
        html = game.pop("boxscore_html", None)
        if html:
            game_id = f"{game.get('date','')}_{game.get('away','')}_at_{game.get('home','')}"
            path = save_boxscore_html("season", html, game_id)
            game["boxscore"] = path
        save_schedule(self.simulator.schedule, SCHEDULE_FILE)

        # Update detailed standings splits from the game's result.
        result = game.get("result")
        try:
            if result:
                home_score, away_score = map(int, result.split("-"))
                home_id = game.get("home", "")
                away_id = game.get("away", "")
                if not home_id or not away_id:
                    raise ValueError("missing team identifiers")
                home_rec = self._standings.setdefault(home_id, default_record())
                away_rec = self._standings.setdefault(away_id, default_record())
                meta = game.get("extra") or {}
                one_run = abs(home_score - away_score) == 1
                extra_innings = bool(meta.get("extra_innings"))
                home_hand = (meta.get("home_starter_hand") or "").upper()
                away_hand = (meta.get("away_starter_hand") or "").upper()
                home_div = self._team_divisions.get(home_id)
                away_div = self._team_divisions.get(away_id)
                division_game = bool(home_div and away_div and home_div == away_div)
                update_record(
                    home_rec,
                    won=home_score > away_score,
                    runs_for=home_score,
                    runs_against=away_score,
                    home=True,
                    opponent_hand=away_hand,
                    division_game=division_game,
                    one_run=one_run,
                    extra_innings=extra_innings,
                )
                update_record(
                    away_rec,
                    won=away_score > home_score,
                    runs_for=away_score,
                    runs_against=home_score,
                    home=False,
                    opponent_hand=home_hand,
                    division_game=division_game,
                    one_run=one_run,
                    extra_innings=extra_innings,
                )
        except ValueError:
            pass

        with (DATA_DIR / "standings.json").open("w", encoding="utf-8") as fh:
            json.dump(self._standings, fh, indent=2)

    # ------------------------------------------------------------------
    # Lineup validation/repair helpers
    def _team_lineup_is_valid(self, team_id: str) -> bool:
        """Return True if both vs_lhp and vs_rhp are valid 9-hitter lineups.

        Valid means: file exists, 9 unique players, all on ACT roster, and no
        pitchers included. Pitchers are detected using player metadata and
        ``get_role`` ("SP"/"RP" count as pitchers).
        """
        try:
            roster = load_roster(team_id)
        except Exception:
            return False
        act = set(roster.act)
        try:
            players_meta = {
                p.player_id: p for p in load_players_from_csv(DATA_DIR / "players.csv")
            }
        except Exception:
            players_meta = {}
        for vs in ("lhp", "rhp"):
            try:
                lineup = load_lineup(team_id, vs=vs, lineup_dir=DATA_DIR / "lineups")
            except Exception:
                return False
            ids = [pid for pid, _ in lineup]
            if len(set(ids)) != 9 or len(ids) != 9:
                return False
            if any(pid not in act for pid in ids):
                return False
            # Ensure no pitchers included
            for pid in ids:
                p = players_meta.get(pid)
                if p is None:
                    # If we cannot resolve metadata, fall back to allowing
                    # this player to avoid false negatives.
                    continue
                role = get_role(p)
                if getattr(p, "is_pitcher", False) or role in {"SP", "RP"}:
                    return False
        return True

    def _repair_lineups(self) -> None:
        from utils.lineup_autofill import auto_fill_lineup_for_team
        fixed = 0
        failed: list[str] = []
        try:
            teams = load_teams(DATA_DIR / "teams.csv")
        except Exception as exc:
            QMessageBox.warning(self, "Repair Lineups", f"Failed to load teams: {exc}")
            return
        for team in teams:
            try:
                if not self._team_lineup_is_valid(team.team_id):
                    auto_fill_lineup_for_team(team.team_id)
                    if self._team_lineup_is_valid(team.team_id):
                        fixed += 1
                    else:
                        failed.append(team.team_id)
            except Exception:
                failed.append(team.team_id)
        if failed:
            QMessageBox.warning(
                self,
                "Repair Lineups",
                f"Repaired {fixed} teams, but these still need attention: {', '.join(failed)}",
            )
        else:
            QMessageBox.information(self, "Repair Lineups", f"Repaired {fixed} team lineups.")

    # ------------------------------------------------------------------
    # Lineup validation helpers
    def _validate_all_team_lineups(self) -> list[str]:
        """Return a list of issues if any team lacks valid 9-man lineups.

        A lineup is considered valid if both ``vs_lhp`` and ``vs_rhp`` files
        exist for the team, contain 9 unique player_ids, and every player is on
        the team's ACT roster. The message is concise to guide correction.
        """
        issues: list[str] = []
        try:
            teams = load_teams(DATA_DIR / "teams.csv")
        except Exception:
            return issues
        try:
            players_meta = {p.player_id: p for p in load_players_from_csv(DATA_DIR / "players.csv")}
        except Exception:
            players_meta = {}
        for team in teams:
            try:
                roster = load_roster(team.team_id)
            except Exception:
                issues.append(f"{team.team_id}: missing roster file")
                continue
            act = set(roster.act)
            for vs in ("lhp", "rhp"):
                try:
                    lineup = load_lineup(team.team_id, vs=vs, lineup_dir=DATA_DIR / "lineups")
                except FileNotFoundError:
                    issues.append(f"{team.team_id}: missing lineup vs_{vs}")
                    continue
                except ValueError:
                    issues.append(f"{team.team_id}: invalid lineup vs_{vs}")
                    continue
                ids = [pid for pid, _ in lineup]
                if len(set(ids)) != 9 or len(ids) != 9:
                    issues.append(f"{team.team_id}: vs_{vs} must list 9 unique players")
                    continue
                missing = [pid for pid in ids if pid not in act]
                if missing:
                    issues.append(f"{team.team_id}: vs_{vs} includes non-ACT players: {', '.join(missing)}")
                    continue
                # Ensure all lineup players are non-pitchers (eligible hitters)
                bad_roles = []
                for pid in ids:
                    p = players_meta.get(pid)
                    if p is None:
                        continue
                    if getattr(p, "is_pitcher", False) or get_role(p) in {"SP", "RP"}:
                        bad_roles.append(pid)
                if bad_roles:
                    issues.append(f"{team.team_id}: vs_{vs} contains pitchers: {', '.join(bad_roles)}")
        return issues

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def _schedule_unknown_team_ids(self) -> list[str]:
        """Return schedule team IDs not present in teams.csv.

        Compares the set of IDs appearing in the current schedule's "home" and
        "away" fields against the loaded teams list. The comparison is
        normalization-insensitive: IDs are compared after ``strip()`` and
        ``upper()`` to avoid false positives from stray whitespace or case
        differences in CSVs.
        """
        # Collect raw IDs as they appear in the schedule so any message can
        # show the exact values found, but compare using normalized forms.
        sched_ids_raw: list[str] = []
        for g in self.simulator.schedule:
            home_raw = str(g.get("home", ""))
            away_raw = str(g.get("away", ""))
            if home_raw:
                sched_ids_raw.append(home_raw)
            if away_raw:
                sched_ids_raw.append(away_raw)

        def _norm(s: str) -> str:
            return str(s).strip().upper()

        known_norm = { _norm(k) for k in self._team_divisions.keys() }
        unknown: set[str] = set()
        for tid in sched_ids_raw:
            if _norm(tid) and _norm(tid) not in known_norm:
                # Preserve original token to aid user diagnosis, but ensure
                # uniqueness via set semantics.
                unknown.add(tid)
        return sorted(unknown)

    def _ensure_valid_schedule_teams(self) -> bool:
        """Prompt to regenerate schedule if it references unknown teams.

        Returns True if the schedule is valid or was regenerated; False if the
        user declined regeneration (so callers should abort simulation).
        """
        unknown = self._schedule_unknown_team_ids()
        if not unknown:
            return True
        # Do not overwrite an in-progress season. If any games are already
        # complete (by index or inferred from schedule flags), keep the
        # existing schedule and simply inform the user.
        progressed = False
        try:
            progressed = int(self.simulator._index or 0) > 0
        except Exception:
            progressed = False
        if not progressed:
            try:
                inferred = self._infer_sim_index_from_schedule()
                progressed = inferred > 0
            except Exception:
                progressed = False
        if progressed:
            try:
                QMessageBox.information(
                    self,
                    "Schedule Contains Unknown Teams",
                    (
                        "Some team IDs in the schedule are not present in teams.csv, "
                        "but the season has already progressed. Keeping existing schedule."
                    ),
                )
            except Exception:
                pass
            return True
        try:
            reply = QMessageBox.question(
                self,
                "Invalid Schedule",
                (
                    "Schedule references unknown team IDs: "
                    + ", ".join(unknown)
                    + "\nRegenerate schedule now?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
        except Exception:
            # In headless contexts, default to regenerating
            reply = QMessageBox.StandardButton.Yes  # type: ignore[attr-defined]
        if reply == QMessageBox.StandardButton.Yes:
            self._generate_schedule()
            return True
        # Leave a helpful note if the user declines
        self._update_ui(
            "Schedule contains unknown teams; please regenerate the schedule."
        )
        return False

    def _load_progress(self) -> None:
        """Load preseason and simulation progress from disk."""
        saved_index: int | None = None
        try:
            with PROGRESS_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._preseason_done.update(data.get("preseason_done", {}))
            # Saved index may be absent or out of range after refactors
            raw = data.get("sim_index", None)
            if isinstance(raw, int):
                saved_index = raw
            self._playoffs_done = data.get("playoffs_done", self._playoffs_done)
        except (OSError, json.JSONDecodeError):
            # No saved file or invalid JSON â€” fall back to inference
            pass

        inferred_index = self._infer_sim_index_from_schedule()
        # Prefer the larger of saved vs inferred to avoid regressing progress
        if saved_index is None:
            new_index = inferred_index
        else:
            new_index = max(int(saved_index), int(inferred_index))

        # Clamp to available date range
        if self.simulator.dates:
            new_index = max(0, min(new_index, len(self.simulator.dates)))
        else:
            new_index = 0

        self.simulator._index = new_index
        # Persist a repaired/initialized progress file for future runs only
        # when it changes, to avoid clobbering progress in transient error cases.
        try:
            cur_idx = None
            try:
                with PROGRESS_FILE.open("r", encoding="utf-8") as fh:
                    cur = json.load(fh)
                cur_idx = int(cur.get("sim_index", 0) or 0)
            except Exception:
                cur_idx = None
            if cur_idx is None or int(new_index) != int(cur_idx):
                self._save_progress()
        except Exception:
            pass

    def _infer_sim_index_from_schedule(self) -> int:
        """Infer current day index from the schedule file/state.

        A date is considered completed if all games for that date have
        a truthy "played" flag or contain a result. This allows recovering
        progress when ``season_progress.json`` is missing or stale but the
        schedule and standings have persisted across code changes.
        """
        if not self.simulator.schedule or not self.simulator.dates:
            return 0
        by_date: dict[str, list[dict[str, str]]] = {}
        for g in self.simulator.schedule:
            by_date.setdefault(g.get("date", ""), []).append(g)
        completed_days = 0
        for d in self.simulator.dates:
            games = by_date.get(d, [])
            if not games:
                break
            all_done = True
            for game in games:
                played = game.get("played")
                result = game.get("result")
                if not (str(played).strip() == "1" or (result and str(result).strip())):
                    all_done = False
                    break
            if all_done:
                completed_days += 1
            else:
                break
        return completed_days

    def _save_progress(self) -> None:
        """Persist preseason and simulation progress to disk."""
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Merge with existing progress so we don't drop fields like
        # "draft_completed_years" that may be written elsewhere (e.g., on
        # Draft Day completion). This avoids re-triggering the draft.
        existing: dict[str, object] = {}
        try:
            if PROGRESS_FILE.exists():
                with PROGRESS_FILE.open("r", encoding="utf-8") as fh:
                    existing = json.load(fh) or {}
        except Exception:
            existing = {}

        existing["preseason_done"] = self._preseason_done
        existing["sim_index"] = self.simulator._index
        existing["playoffs_done"] = self._playoffs_done

        with PROGRESS_FILE.open("w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2)
        # Notify listeners that the date may have advanced
        cur: str | None = None
        try:
            cur = get_current_sim_date()
            self.progressUpdated.emit(cur or "")
        except Exception:
            pass
        try:
            notify_sim_date_changed(cur)
        except Exception:
            pass

