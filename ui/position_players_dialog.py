"""Dialog for viewing position players grouped by roster level and position."""

from datetime import datetime
from typing import Dict, Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QVBoxLayout,
)

from ui.player_profile_dialog import PlayerProfileDialog

from models.base_player import BasePlayer
from models.roster import Roster
from utils.pitcher_role import get_role


class PositionPlayersDialog(QDialog):
    """Display all position players grouped by roster level and position."""

    position_order = ["C", "1B", "2B", "SS", "3B", "LF", "CF", "RF"]

    def __init__(self, players: Dict[str, BasePlayer], roster: Roster, parent=None):
        super().__init__(parent)
        self.players = players
        self.roster = roster

        self.setWindowTitle("Position Players")

        layout = QVBoxLayout()
        layout.addWidget(self._build_level_section("ACT", roster.act))
        layout.addWidget(self._build_level_section("AAA", roster.aaa))
        layout.addWidget(self._build_level_section("LOW", roster.low))
        layout.addStretch()
        self.setLayout(layout)

        size = self.sizeHint()
        self.resize(size.width() * 2, size.height())

    # ------------------------------------------------------------------
    # Section builders
    def _build_level_section(self, label: str, player_ids: Iterable[str]) -> QGroupBox:
        """Create a section showing position players for a single level."""

        level_box = QGroupBox(label)
        layout = QVBoxLayout()

        groups = {}
        for pid in player_ids:
            p = self.players.get(pid)
            if not p or get_role(p):
                continue
            groups.setdefault(p.primary_position, []).append(p)

        tab_widget = QTabWidget()
        for position in self.position_order:
            players = groups.get(position)
            if not players:
                continue
            lw = QListWidget()
            for player in players:
                lw.addItem(self._make_player_item(player))
            lw.itemDoubleClicked.connect(self._open_player_profile)
            tab_widget.addTab(lw, position)

        layout.addWidget(tab_widget)
        level_box.setLayout(layout)
        return level_box

    # ------------------------------------------------------------------
    # Helpers
    def _make_player_item(self, p: BasePlayer) -> QListWidgetItem:
        """Format a player entry similar to OwnerDashboard._make_player_item."""

        age = self._calculate_age(p.birthdate)
        role = get_role(p)
        if role:
            core = f"AS:{getattr(p, 'arm', 0)} EN:{getattr(p, 'endurance', 0)} CO:{getattr(p, 'control', 0)}"
        else:
            core = f"CH:{getattr(p, 'ch', 0)} PH:{getattr(p, 'ph', 0)} SP:{getattr(p, 'sp', 0)}"
        label = f"{p.first_name} {p.last_name} ({age}) - {role or p.primary_position} | {core}"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, p.player_id)
        return item

    def _calculate_age(self, birthdate_str: str):
        try:
            birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            return today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )
        except Exception:
            return "?"

    # ------------------------------------------------------------------
    # Player profile dialog
    def _open_player_profile(self, item: QListWidgetItem):
        """Open the player profile dialog for the selected item."""
        pid = item.data(Qt.ItemDataRole.UserRole)
        player = self.players.get(pid)
        if not player:
            return
        PlayerProfileDialog(player, self).exec()

