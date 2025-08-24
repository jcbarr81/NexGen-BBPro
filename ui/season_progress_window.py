from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
    QProgressDialog,
)
from datetime import date
import csv
import json
from pathlib import Path

import logic.season_manager as season_manager
from logic.aging_model import age_and_retire
from logic.season_manager import SeasonManager, SeasonPhase
from logic.training_camp import run_training_camp
from services.free_agency import list_unsigned_players
from logic.season_simulator import SeasonSimulator
from logic.schedule_generator import generate_mlb_schedule, save_schedule
from utils.news_logger import log_news_event


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TEAMS_FILE = DATA_DIR / "teams.csv"
SCHEDULE_FILE = DATA_DIR / "schedule.csv"
PROGRESS_FILE = DATA_DIR / "season_progress.json"


class SeasonProgressWindow(QDialog):
    """Dialog displaying the current season phase and progress notes."""

    def __init__(
        self,
        parent=None,
        schedule: list[dict[str, str]] | None = None,
        simulate_game=None,
    ) -> None:
        super().__init__(parent)
        try:
            self.setWindowTitle("Season Progress")
            self.setMinimumSize(300, 200)
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
        self.simulator = SeasonSimulator(
            schedule or [], simulate_game, after_game=self._record_game
        )
        self._preseason_done = {
            "free_agency": False,
            "training_camp": False,
            "schedule": False,
        }
        self._load_progress()

        layout = QVBoxLayout(self)

        self.phase_label = QLabel()
        layout.addWidget(self.phase_label)

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

        self.next_button = QPushButton("Next Phase")
        self.next_button.clicked.connect(self._next_phase)
        layout.addWidget(self.next_button)

        self._update_ui()

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
        if note is None:
            note = self.manager.handle_phase()
        self.notes_label.setText(note)

        is_preseason = self.manager.phase == SeasonPhase.PRESEASON
        is_regular = self.manager.phase == SeasonPhase.REGULAR_SEASON
        self.free_agency_button.setVisible(is_preseason)
        self.training_camp_button.setVisible(is_preseason)
        self.generate_schedule_button.setVisible(is_preseason)
        self.remaining_label.setVisible(is_regular)
        self.simulate_day_button.setVisible(is_regular)
        self.simulate_week_button.setVisible(is_regular)
        self.simulate_month_button.setVisible(is_regular)
        if is_regular:
            remaining = self.simulator.remaining_days()
            self.remaining_label.setText(f"Days until Midseason: {remaining}")
            enabled = remaining > 0
            self.simulate_day_button.setEnabled(enabled)
            self.simulate_week_button.setEnabled(enabled)
            self.simulate_month_button.setEnabled(enabled)
            season_done = self.simulator._index >= len(self.simulator.dates)
            self.next_button.setEnabled(season_done or not enabled)
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
            self.next_button.setEnabled(self._preseason_done["schedule"])
        else:
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
            self.simulator = SeasonSimulator([], self._simulate_game)
            note = f"Retired Players: {len(retired)}"
        else:
            self.manager.advance_phase()
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
        self.simulator = SeasonSimulator(
            schedule, self._simulate_game, after_game=self._record_game
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
        if self.simulator.remaining_days() <= 0:
            return
        try:
            self.simulator.simulate_next_day()
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(
                self, "Missing Lineup or Pitching", str(e)
            )
            return
        remaining = self.simulator.remaining_days()
        self.remaining_label.setText(f"Days until Midseason: {remaining}")
        log_news_event(
            f"Simulated a regular season day; {remaining} days until Midseason"
        )
        self._save_progress()
        season_done = self.simulator._index >= len(self.simulator.dates)
        if remaining <= 0 or season_done:
            self.simulate_day_button.setEnabled(False)
            self.simulate_week_button.setEnabled(False)
            self.simulate_month_button.setEnabled(False)
            self.next_button.setEnabled(True)

    def _simulate_span(self, days: int, label: str) -> None:
        """Simulate multiple days with a progress dialog."""
        if self.simulator.remaining_days() <= 0:
            return
        progress = QProgressDialog(
            f"Simulating {label}...", None, 0, days, self
        )
        try:  # pragma: no cover - harmless in headless tests
            progress.setWindowTitle("Simulation Progress")
            progress.setValue(0)
            progress.show()
        except Exception:  # pragma: no cover
            pass
        simulated = 0
        while simulated < days and self.simulator.remaining_days() > 0:
            try:
                self.simulator.simulate_next_day()
            except (FileNotFoundError, ValueError) as e:
                QMessageBox.warning(
                    self, "Missing Lineup or Pitching", str(e)
                )
                break
            simulated += 1
            try:  # pragma: no cover - gui only
                progress.setValue(simulated)
            except Exception:  # pragma: no cover
                pass
        try:  # pragma: no cover - gui only
            progress.close()
        except Exception:  # pragma: no cover
            pass
        remaining = self.simulator.remaining_days()
        self.remaining_label.setText(f"Days until Midseason: {remaining}")
        log_news_event(
            f"Simulated {label.lower()}; {remaining} days until Midseason"
        )
        self._save_progress()
        season_done = self.simulator._index >= len(self.simulator.dates)
        if remaining <= 0 or season_done:
            self.simulate_day_button.setEnabled(False)
            self.simulate_week_button.setEnabled(False)
            self.simulate_month_button.setEnabled(False)
            self.next_button.setEnabled(True)

    def _simulate_week(self) -> None:
        """Simulate the next seven days or until the break."""
        self._simulate_span(7, "Week")

    def _simulate_month(self) -> None:
        """Simulate the next thirty days or until the break."""
        self._simulate_span(30, "Month")

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
        save_schedule(self.simulator.schedule, SCHEDULE_FILE)

        # Save team standings and player statistics if available.  These
        # attributes are optional so the method is defensive when accessing
        # them.
        standings = {}
        if hasattr(self.manager, "teams"):
            for team in getattr(self.manager, "teams", []):
                tid = getattr(team, "abbreviation", getattr(team, "team_id", ""))
                standings[tid] = getattr(team, "season_stats", {})

        players_stats = {}
        if hasattr(self.manager, "players"):
            for pid, player in getattr(self.manager, "players", {}).items():
                players_stats[pid] = getattr(player, "season_stats", {})

        if standings:
            with (DATA_DIR / "standings.json").open("w", encoding="utf-8") as fh:
                json.dump(standings, fh, indent=2)
        if players_stats:
            with (DATA_DIR / "player_stats.json").open("w", encoding="utf-8") as fh:
                json.dump(players_stats, fh, indent=2)

    def _load_progress(self) -> None:
        """Load preseason and simulation progress from disk."""
        try:
            with PROGRESS_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        self._preseason_done.update(data.get("preseason_done", {}))
        self.simulator._index = data.get("sim_index", self.simulator._index)

    def _save_progress(self) -> None:
        """Persist preseason and simulation progress to disk."""
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "preseason_done": self._preseason_done,
            "sim_index": self.simulator._index,
        }
        with PROGRESS_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

