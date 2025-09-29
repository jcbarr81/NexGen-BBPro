from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from .components import Card, section_title
from utils.roster_validation import missing_positions


class RosterPage(QWidget):
    """Page with shortcuts for roster-related tasks."""

    def __init__(self, dashboard):
        super().__init__()
        self._dashboard = dashboard
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("Roster Management"))

        # Coverage notice label (updated via refresh())
        self.coverage_label = QLabel("")
        card.layout().addWidget(self.coverage_label)

        btn_players = QPushButton("Players", objectName="Primary")
        btn_players.setToolTip("Browse all position players and pitchers")
        btn_players.clicked.connect(dashboard.open_player_browser_dialog)
        card.layout().addWidget(btn_players)

        btn_pitch = QPushButton("Pitching Staff", objectName="Primary")
        btn_pitch.clicked.connect(dashboard.open_pitching_editor)
        card.layout().addWidget(btn_pitch)

        btn_lineups = QPushButton("Lineups", objectName="Primary")
        btn_lineups.clicked.connect(dashboard.open_lineup_editor)
        card.layout().addWidget(btn_lineups)

        btn_move = QPushButton("Reassign Players", objectName="Primary")
        btn_move.clicked.connect(dashboard.open_reassign_players_dialog)
        card.layout().addWidget(btn_move)

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()

    def refresh(self) -> None:
        """Update defensive coverage notice based on current roster."""
        try:
            roster = getattr(self._dashboard, "roster", None)
            players = getattr(self._dashboard, "players", {})
            missing = missing_positions(roster, players) if roster else []
        except Exception:
            missing = []
        if missing:
            text = "Missing coverage: " + ", ".join(missing)
            # Use a warm accent color that fits both themes
            self.coverage_label.setStyleSheet("color: #e67700; font-weight: 600;")
        else:
            text = "Defensive coverage looks good."
            self.coverage_label.setStyleSheet("color: #2f9e44; font-weight: 600;")
        self.coverage_label.setText(text)
