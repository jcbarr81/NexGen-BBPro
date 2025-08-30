from __future__ import annotations

"""Dialog allowing owners to move players between roster levels."""

from typing import Dict

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QMessageBox,
    QPushButton,
)

from models.base_player import BasePlayer
from models.roster import Roster
from services.roster_moves import move_player_between_rosters


class MovePlayerDialog(QDialog):
    """Simple dialog for moving a player to a different roster level."""

    levels = ("act", "aaa", "low")

    def __init__(self, players: Dict[str, BasePlayer], roster: Roster, parent=None):
        super().__init__(parent)
        self.players = players
        self.roster = roster

        self.setWindowTitle("Move Player")

        self.player_combo = QComboBox()
        for level in self.levels:
            for pid in getattr(roster, level):
                player = players.get(pid)
                if not player:
                    continue
                label = f"{player.first_name} {player.last_name} ({level.upper()})"
                self.player_combo.addItem(label, (pid, level))
        self.player_combo.currentIndexChanged.connect(self._update_destinations)

        self.dest_combo = QComboBox()
        self._update_destinations()

        move_btn = QPushButton("Move")
        move_btn.clicked.connect(self._move_player)

        layout = QFormLayout(self)
        layout.addRow("Player", self.player_combo)
        layout.addRow("Destination", self.dest_combo)
        layout.addRow(move_btn)

    def _update_destinations(self) -> None:
        data = self.player_combo.currentData()
        self.dest_combo.clear()
        if not data:
            return
        _pid, source = data
        for level in self.levels:
            if level != source:
                self.dest_combo.addItem(level.upper(), level)

    def _move_player(self) -> None:
        data = self.player_combo.currentData()
        if not data:
            return
        pid, source = data
        dest = self.dest_combo.currentData()
        if not dest:
            return
        try:
            move_player_between_rosters(pid, self.roster, source, dest)
            QMessageBox.information(
                self, "Move Player", "Player moved successfully."
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
