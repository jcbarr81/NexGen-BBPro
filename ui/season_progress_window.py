from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from logic.season_manager import SeasonManager


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

    def _next_phase(self) -> None:
        """Advance to the next phase and update the display."""
        self.manager.advance_phase()
        self._update_ui()

