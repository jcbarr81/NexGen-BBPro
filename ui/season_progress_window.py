from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from datetime import date

import logic.season_manager as season_manager
from logic.aging_model import age_and_retire
from logic.season_manager import SeasonManager, SeasonPhase
from logic.training_camp import run_training_camp
from services.free_agency import list_unsigned_players
from logic.season_simulator import SeasonSimulator
from utils.news_logger import log_news_event


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
        self.simulator = SeasonSimulator(schedule or [], simulate_game)

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
    def _update_ui(self) -> None:
        """Refresh the label and notes for the current phase."""
        phase_name = self.manager.phase.name.replace("_", " ").title()
        self.phase_label.setText(f"Current Phase: {phase_name}")
        notes = self.manager.handle_phase()
        self.notes_label.setText(notes)

        is_preseason = self.manager.phase == SeasonPhase.PRESEASON
        is_regular = self.manager.phase == SeasonPhase.REGULAR_SEASON
        self.free_agency_button.setVisible(is_preseason)
        self.training_camp_button.setVisible(is_preseason)
        self.remaining_label.setVisible(is_regular)
        self.simulate_day_button.setVisible(is_regular)
        if is_regular:
            remaining = self.simulator.remaining_days()
            self.remaining_label.setText(f"Days until Midseason: {remaining}")

    def _next_phase(self) -> None:
        """Advance to the next phase and update the display."""
        if self.manager.phase == SeasonPhase.OFFSEASON:
            players = getattr(self.manager, "players", {})
            retired = age_and_retire(players)
            self.notes_label.setText(f"Retired Players: {len(retired)}")
            season_manager.TRADE_DEADLINE = date(date.today().year + 1, 7, 31)
            self.manager.phase = SeasonPhase.PRESEASON
            self.manager.save()
        else:
            self.manager.advance_phase()
        log_news_event(
            f"Season advanced to {self.manager.phase.name.replace('_', ' ').title()}"
        )
        self._update_ui()

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

    def _run_training_camp(self) -> None:
        """Run the training camp and mark players as ready."""
        players = getattr(self.manager, "players", {})
        run_training_camp(players.values())
        self.notes_label.setText("Training camp completed. Players marked ready.")
        log_news_event("Training camp completed; players marked ready")

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

