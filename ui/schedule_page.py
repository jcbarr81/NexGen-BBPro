from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from .components import Card, section_title


class SchedulePage(QWidget):
    """Page for viewing league schedules and information."""

    def __init__(self, dashboard):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("League"))

        btn_league = QPushButton("League Schedule", objectName="Primary")
        btn_league.clicked.connect(dashboard.open_schedule_window)
        card.layout().addWidget(btn_league)

        btn_standings = QPushButton("Standings", objectName="Primary")
        btn_standings.clicked.connect(dashboard.open_standings_window)
        card.layout().addWidget(btn_standings)

        btn_stats = QPushButton("League Stats", objectName="Primary")
        btn_stats.clicked.connect(dashboard.open_league_stats_window)
        card.layout().addWidget(btn_stats)

        btn_leaders = QPushButton("League Leaders", objectName="Primary")
        btn_leaders.clicked.connect(dashboard.open_league_leaders_window)
        card.layout().addWidget(btn_leaders)

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()
