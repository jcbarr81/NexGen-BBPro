"""Team management helpers migrated from the legacy admin dashboard."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ...components import Card, section_title
from .base import DashboardPage

from utils.team_loader import load_teams


class TeamsPage(DashboardPage):
    """Team management helpers, grouped for access and bulk actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        access = Card()
        access.layout().addWidget(section_title("Team Access"))

        self.team_select = QComboBox()
        try:
            teams = load_teams("data/teams.csv")
            self.team_select.addItems([t.team_id for t in teams])
        except Exception:
            pass
        self.team_select.setEditable(True)
        self.team_select.setToolTip("Type to search by team id; used by 'Open Team Dashboard'")
        access.layout().addWidget(self.team_select)

        self.team_dashboard_button = QPushButton("Open Team Dashboard")
        self.team_dashboard_button.setToolTip("Open selected team's Owner Dashboard")
        access.layout().addWidget(self.team_dashboard_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        access.layout().addStretch()

        bulk = Card()
        bulk.layout().addWidget(section_title("Bulk Actions"))

        self.set_lineups_button = QPushButton("Set All Team Lineups")
        self.set_lineups_button.setToolTip("Auto-fill batting orders for all teams")
        bulk.layout().addWidget(self.set_lineups_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.set_pitching_button = QPushButton("Set All Pitching Staff Roles")
        self.set_pitching_button.setToolTip("Auto-assign pitching roles for all teams")
        bulk.layout().addWidget(self.set_pitching_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.auto_reassign_button = QPushButton("Auto Reassign All Rosters")
        self.auto_reassign_button.setToolTip("Reassign players across roster levels using policy constraints")
        bulk.layout().addWidget(self.auto_reassign_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        note = QLabel("Actions affect all teams. Constraints: Active <= 25; AAA <= 15; Low <= 10.")
        note.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        bulk.layout().addWidget(note)
        bulk.layout().addStretch()

        layout.addWidget(access)
        layout.addWidget(bulk)
        layout.addStretch()

    def refresh(self) -> None:
        """Repopulate the teams dropdown from the current league file."""
        try:
            teams = load_teams("data/teams.csv")
        except Exception:
            teams = []
        try:
            self.team_select.blockSignals(True)
            self.team_select.clear()
            self.team_select.addItems([t.team_id for t in teams])
        except Exception:
            pass
        finally:
            try:
                self.team_select.blockSignals(False)
            except Exception:
                pass


__all__ = ["TeamsPage"]
