from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from .components import Card, section_title


class RosterPage(QWidget):
    """Page with shortcuts for roster-related tasks."""

    def __init__(self, dashboard):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("Roster Management"))

        btn_pos = QPushButton("Position Players", objectName="Primary")
        btn_pos.clicked.connect(dashboard.open_position_players_dialog)
        card.layout().addWidget(btn_pos)

        btn_pitch = QPushButton("Pitching Staff", objectName="Primary")
        btn_pitch.clicked.connect(dashboard.open_pitching_editor)
        card.layout().addWidget(btn_pitch)

        btn_lineups = QPushButton("Lineups", objectName="Primary")
        btn_lineups.clicked.connect(dashboard.open_lineup_editor)
        card.layout().addWidget(btn_lineups)

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()
