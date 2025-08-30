from __future__ import annotations

"""Dialog allowing owners to reassign players between roster levels."""

from typing import Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QMessageBox,
    QPushButton,
)

from models.base_player import BasePlayer
from models.roster import Roster
from services.roster_moves import move_player_between_rosters


class ReassignPlayersDialog(QDialog):
    """Dialog for reassigning players to different roster levels."""

    levels = ("act", "aaa", "low")

    def __init__(self, players: Dict[str, BasePlayer], roster: Roster, parent=None):
        super().__init__(parent)
        self.players = players
        self.roster = roster

        self.setWindowTitle("Reassign Players")

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Player", "Current", "Destination"])

        for level in self.levels:
            for pid in getattr(roster, level):
                player = players.get(pid)
                if not player:
                    continue
                row = self.table.rowCount()
                self.table.insertRow(row)

                name_item = QTableWidgetItem(
                    f"{player.first_name} {player.last_name}"
                )
                name_item.setData(Qt.ItemDataRole.UserRole, pid)
                self.table.setItem(row, 0, name_item)

                current_item = QTableWidgetItem(level.upper())
                current_item.setData(Qt.ItemDataRole.UserRole, level)
                self.table.setItem(row, 1, current_item)

                dest_combo = QComboBox()
                for lvl in self.levels:
                    if lvl != level:
                        dest_combo.addItem(lvl.upper(), lvl)
                self.table.setCellWidget(row, 2, dest_combo)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        move_btn = QPushButton("Reassign")
        move_btn.clicked.connect(self._apply_moves)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(move_btn)

        height = (
            self.table.verticalHeader().length()
            + self.table.horizontalHeader().height()
            + 80
        )
        width = self.table.horizontalHeader().length() + 40
        self.resize(width, height)

    def _apply_moves(self) -> None:
        moved = False
        for row in range(self.table.rowCount()):
            pid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            current = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            combo = self.table.cellWidget(row, 2)
            dest = combo.currentData()
            if dest and dest != current:
                try:
                    move_player_between_rosters(pid, self.roster, current, dest)
                    moved = True
                except Exception as exc:
                    QMessageBox.critical(self, "Error", str(exc))
                    return

        if moved:
            QMessageBox.information(
                self, "Reassign Players", "Players reassigned successfully."
            )
            self.accept()
        else:
            self.reject()
