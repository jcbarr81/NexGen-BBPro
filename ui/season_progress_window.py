from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from logic.season_manager import SeasonManager, SeasonPhase
from logic.training_camp import run_training_camp
from services.free_agency import list_unsigned_players


class SeasonProgressWindow(QDialog):
    """Dialog displaying the current season phase and progress notes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        try:
            self.setWindowTitle("Season Progress")
        except Exception:  # pragma: no cover - harmless in headless tests
            pass

        self.manager = SeasonManager()

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
        self.free_agency_button.setVisible(is_preseason)
        self.training_camp_button.setVisible(is_preseason)

    def _next_phase(self) -> None:
        """Advance to the next phase and update the display."""
        self.manager.advance_phase()
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
        else:
            self.notes_label.setText("No unsigned players available.")

    def _run_training_camp(self) -> None:
        """Run the training camp and mark players as ready."""
        players = getattr(self.manager, "players", {})
        run_training_camp(players.values())
        self.notes_label.setText("Training camp completed. Players marked ready.")

