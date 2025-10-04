from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
    QProgressDialog,
)
from PyQt6.QtCore import pyqtSignal
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


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TEAMS_FILE = DATA_DIR / "teams.csv"
SCHEDULE_FILE = DATA_DIR / "schedule.csv"
PROGRESS_FILE = DATA_DIR / "season_progress.json"


class SeasonProgressWindow(QDialog):
    """Dialog displaying the current season phase and progress notes."""

    # Emitted whenever season progress persists a new date, or when closing
    # the window. Carries the latest current sim date string.
    progressUpdated = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        schedule: list[dict[str, str]] | None = None,
        simulate_game=None,
    ) -> None:
        super().__init__(parent)
        try:
            self.setWindowTitle("Season Progress")
            self.setMinimumSize(320, 280)
        except Exception:  # pragma: no cover - harmless in headless tests
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

        self.simulate_day_button = QPushButton("Simulate Day")
        self.simulate_day_button.clicked.connect(self._simulate_day)
        layout.addWidget(self.simulate_day_button)

        self.simulate_week_button = QPushButton("Simulate Week")
        self.simulate_week_button.clicked.connect(self._simulate_week)
        layout.addWidget(self.simulate_week_button)

        self.simulate_month_button = QPushButton("Simulate Month")
        self.simulate_month_button.clicked.connect(self._simulate_month)
        layout.addWidget(self.simulate_month_button)

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

    def _on_draft_day(self, date_str: str) -> None:
        # Skip if already completed for this year
        try:
            import json as _json
            year = int(str(date_str).split("-")[0])
            progress = {}
            if PROGRESS_FILE.exists():
                try:
                    progress = _json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    progress = {}
            completed = set(progress.get("draft_completed_years", []))
            if year in completed:
                return
            # Enter Amateur Draft phase
            try:
                self.manager.phase = SeasonPhase.AMATEUR_DRAFT
                self.manager.save()
                self._update_ui("Amateur Draft Day: paused for draft operations.")
            except Exception:
                pass
            try:
                dlg = DraftConsole(date_str, self)
                dlg.exec()
                summary = dict(getattr(dlg, "assignment_summary", {}) or {})
                failures = list(summary.get("failures") or [])
                compliance = list(summary.get("compliance_issues") or [])
                # If no commit occurred, require it before resuming
                if not summary:
                    failures = [
                        "Draft results must be committed before resuming the season."
                    ]
                # Only hard failures block the season. Compliance issues are surfaced
                # as warnings but do not prevent marking the draft complete.
                if failures:
                    raise DraftRosterError(failures, summary)
                completed.add(year)
                progress["draft_completed_years"] = sorted(completed)
                try:
                    PROGRESS_FILE.write_text(
                        _json.dumps(progress, indent=2), encoding="utf-8"
                    )
                except Exception:
                    pass
                # Return to regular season now that the draft has been
                # committed for this year.
                try:
                    self.manager.phase = SeasonPhase.REGULAR_SEASON
                    self.manager.save()
                    self._update_ui(
                        "Draft committed. Returning to Regular Season."
                    )
                except Exception:
                    pass
            except DraftRosterError:
                # Remain in draft phase when assignments are incomplete
                raise
            except Exception:
                # Generic failure; exit draft phase to avoid blocking simulation in headless tests
                try:
                    self.manager.phase = SeasonPhase.REGULAR_SEASON
                    self.manager.save()
                    self._update_ui("Draft encountered an error; returning to Regular Season.")
                except Exception:
                    pass
        except Exception:
            # Best-effort outer guard: in headless or non-interactive
            # contexts, failures here should not crash the UI.
            pass

    # ------------------------------------------------------------------
    # UI lifecycle
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        try:
            cur = get_current_sim_date()
            self.progressUpdated.emit(cur or "")
        except Exception:
            pass
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _update_ui(self, note: str | None = None) -> None:
        """Refresh the label and notes for the current phase.

        Parameters
        ----------
        note:
            Optional note to display instead of the default phase message.
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
        if is_regular:
            mid_remaining = self.simulator.remaining_days()
            # Draft milestone: only if not yet completed for the season
            draft_remaining = self._days_until_draft()
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
        else:
            self.manager.advance_phase()
            if self.manager.phase == SeasonPhase.PLAYOFFS:
                self._playoffs_done = False
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

    def _simulate_span(self, days: int, label: str) -> None:
        """Simulate multiple days with a progress dialog."""
        if self.simulator.remaining_schedule_days() <= 0:
            return
        # Ensure schedule uses valid team IDs before simulating
        if not self._ensure_valid_schedule_teams():
            return
        # Validate lineups before running a long span
        issues = self._validate_all_team_lineups()
        if issues:
            QMessageBox.warning(self, "Missing Lineup or Pitching", "\n".join(issues))
            return

        # Determine how many individual games will be played in the span so
        # that the progress bar can advance after each contest rather than just
        # once per day.
        start = self.simulator._index
        end = min(start + days, len(self.simulator.dates))
        upcoming = self.simulator.dates[start:end]
        total_games = sum(
            1 for g in self.simulator.schedule if g["date"] in upcoming
        )
        self._cancel_requested = False

        maximum = max(total_games, 1)
        progress = None
        cancel_button = None

        def request_cancel() -> None:
            nonlocal progress, cancel_button
            if self._cancel_requested:
                return
            self._cancel_requested = True
            try:
                if progress is not None:
                    progress.setLabelText("Finishing current day before canceling...")
            except Exception:  # pragma: no cover
                pass
            if cancel_button is not None:
                cancel_button.setEnabled(False)

        try:  # pragma: no cover - harmless in headless tests
            progress = QProgressDialog(
                f"Simulating {label}...", "", 0, maximum, self
            )
            progress.setWindowTitle("Simulation Progress")
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            cancel_button = QPushButton("Cancel Simulation", progress)
            cancel_button.clicked.connect(request_cancel)
            progress.setCancelButton(cancel_button)
            progress.setValue(0)
            progress.canceled.connect(request_cancel)
            progress.show()
            QApplication.processEvents()
        except Exception:  # pragma: no cover
            progress = None
            cancel_button = None

        completed = 0
        original_after = self.simulator.after_game

        def after_game(game):
            nonlocal completed
            completed += 1
            if progress is not None:
                try:  # pragma: no cover - gui only
                    progress.setValue(min(completed, maximum))
                    QApplication.processEvents()
                except Exception:  # pragma: no cover
                    pass
            if original_after is not None:
                try:  # pragma: no cover - best effort for persistence
                    original_after(game)
                except Exception:  # pragma: no cover
                    pass

        self.simulator.after_game = after_game

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
                    failures = getattr(exc, 'failures', None)
                    if failures:
                        message += "\n\n" + "\n".join(failures)
                    QMessageBox.warning(self, "Draft Assignments Incomplete", message)
                    break
                except (FileNotFoundError, ValueError) as e:
                    QMessageBox.warning(
                        self, "Missing Lineup or Pitching", str(e)
                    )
                    break
                simulated_days += 1
                if self._cancel_requested:
                    break
        finally:
            self.simulator.after_game = original_after
            if progress is not None:
                try:  # pragma: no cover - gui only
                    progress.close()
                except Exception:  # pragma: no cover
                    pass
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
        # Treat as "cancelled" only if the user requested cancel and
        # we actually stopped before completing the requested span.
        was_cancelled = bool(self._cancel_requested) and (simulated_days < days)
        self._cancel_requested = False
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
        # Log recaps for each simulated day
        try:
            dates_covered = [str(d) for d in upcoming[:simulated_days]]
            for d in dates_covered:
                self._log_daily_recap_for_date(d)
        except Exception:
            pass
        log_news_event(message, category="progress")
        self._save_progress()
        self._update_ui(message)

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
        """Simulate the postseason bracket and unlock the offseason when done."""
        if self._playoffs_done:
            return
        from playbalance.playoffs_config import load_playoffs_config
        from playbalance.playoffs import (
            load_bracket,
            save_bracket,
            generate_bracket,
            simulate_playoffs as run_playoffs,
        )
        from utils.team_loader import load_teams

        # Load or generate bracket from current standings/teams
        bracket = load_bracket()
        if bracket is None:
            try:
                teams = load_teams()
            except Exception:
                teams = []
            cfg = load_playoffs_config()
            try:
                bracket = generate_bracket(self._standings, teams, cfg)
            except NotImplementedError:
                # Fallback to simple completion if engine not available
                self._playoffs_done = True
                self._save_progress()
                message = "Playoffs placeholder reached; mark as complete."
                log_news_event(message)
        self._update_ui(message)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _days_until_draft(self) -> int:
        """Return days until Draft Day if not yet completed; otherwise 0.

        Counts the number of schedule dates remaining before the inserted Draft
        milestone date. If draft for the simulator's year has already been
        completed (per progress file), returns 0.
        """
        try:
            draft_date = getattr(self.simulator, "draft_date", None)
            if not draft_date:
                return 0
            # Check completion for year
            try:
                year = int(str(draft_date).split("-")[0])
            except Exception:
                return 0
            completed_years: set[int] = set()
            try:
                with PROGRESS_FILE.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                completed_years = set(data.get("draft_completed_years", []))
            except Exception:
                completed_years = set()
            if year in completed_years:
                return 0
            # Find index positions
            dates = list(getattr(self.simulator, "dates", []) or [])
            cur = int(getattr(self.simulator, "_index", 0) or 0)
            try:
                draft_idx = dates.index(str(draft_date))
            except Exception:
                return 0
            if cur < draft_idx:
                return max(0, draft_idx - cur)
            return 0
        except Exception:
            return 0
            save_bracket(bracket)

        # Simulate to completion (persist after each game)
        def _persist(b):
            try:
                save_bracket(b)
            except Exception:
                pass

        try:
            bracket = run_playoffs(bracket, persist_cb=_persist)
        except NotImplementedError:
            # If engine stubbed, exit gracefully
            message = "Playoffs engine not available; cannot simulate."
            log_news_event(message)
            self._update_ui(message)
            return
        except Exception:
            message = "Playoffs simulation encountered an error."
            log_news_event(message)
            self._update_ui(message)
            return

        # If a champion exists, mark playoffs done and write champions.csv with WS result
        if getattr(bracket, "champion", None):
            # Compute WS series result if available
            series_result = ""
            try:
                ws_round = next((r for r in bracket.rounds if r.name in {"WS", "Final"}), None)
                if ws_round and ws_round.matchups:
                    m = ws_round.matchups[0]
                    champ = bracket.champion
                    wins_c = 0
                    wins_o = 0
                    for g in m.games:
                        res = str(g.result or "")
                        if "-" in res:
                            h, a = res.split("-", 1)
                            try:
                                h = int(h)
                                a = int(a)
                            except Exception:
                                continue
                            # Determine winner for each game
                            if h > a:
                                winner = g.home
                            elif a > h:
                                winner = g.away
                            else:
                                continue
                            if winner == champ:
                                wins_c += 1
                            else:
                                wins_o += 1
                    if wins_c or wins_o:
                        series_result = f"{wins_c}-{wins_o}"
            except Exception:
                series_result = ""

            message = f"Simulated playoffs; champion: {bracket.champion}"
            self._playoffs_done = True
            self._save_progress()
            # Append to champions.csv (best-effort)
            try:
                import csv
                champions = (DATA_DIR / "champions.csv")
                champions.parent.mkdir(parents=True, exist_ok=True)
                hdr = ["year", "champion", "runner_up", "series_result"]
                write_header = not champions.exists()
                with champions.open("a", encoding="utf-8", newline="") as fh:
                    w = csv.writer(fh)
                    if write_header:
                        w.writerow(hdr)
                    w.writerow([
                        getattr(bracket, "year", ""),
                        bracket.champion or "",
                        getattr(bracket, "runner_up", "") or "",
                        series_result,
                    ])
            except Exception:
                pass
            log_news_event(message)
            self._update_ui(message)

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
        try:
            cur = get_current_sim_date()
            self.progressUpdated.emit(cur or "")
        except Exception:
            pass

