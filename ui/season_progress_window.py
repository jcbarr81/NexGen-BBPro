from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from datetime import date
import csv
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
        self.simulator = SeasonSimulator(schedule or [], simulate_game)
        self._preseason_done = {
            "free_agency": False,
            "training_camp": False,
            "schedule": False,
        }

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
        if is_regular:
            remaining = self.simulator.remaining_days()
            self.remaining_label.setText(f"Days until Midseason: {remaining}")
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
            note = f"Retired Players: {len(retired)}"
        else:
            self.manager.advance_phase()
            note = None
        log_news_event(
            f"Season advanced to {self.manager.phase.name.replace('_', ' ').title()}"
        )
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
        self._update_ui(message)

    def _run_training_camp(self) -> None:
        """Run the training camp and mark players as ready."""
        players = getattr(self.manager, "players", {})
        run_training_camp(players.values())
        self.notes_label.setText("Training camp completed. Players marked ready.")
        log_news_event("Training camp completed; players marked ready")
        self.training_camp_button.setEnabled(False)
        self._preseason_done["training_camp"] = True
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
        self.simulator = SeasonSimulator(schedule, self._simulate_game)
        message = f"Schedule generated with {len(schedule)} games."
        log_news_event(f"Generated regular season schedule with {len(schedule)} games")
        self.generate_schedule_button.setEnabled(False)
        self._preseason_done["schedule"] = True
        self._update_ui(message)

    # ------------------------------------------------------------------
    # Regular season actions
    # ------------------------------------------------------------------
    def _simulate_day(self) -> None:
        """Trigger simulation for a single schedule day."""
        self.simulator.simulate_next_day()
        remaining = self.simulator.remaining_days()
        self.remaining_label.setText(f"Days until Midseason: {remaining}")
        log_news_event(
            f"Simulated a regular season day; {remaining} days until Midseason"
        )
        season_done = self.simulator._index >= len(self.simulator.dates)
        if season_done:
            self.next_button.setEnabled(True)

