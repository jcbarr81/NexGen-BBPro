from __future__ import annotations

"""Dialog allowing owners to reassign players between roster levels."""

from typing import Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QLabel,
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

        self.lists: Dict[str, QListWidget] = {}
        originals: Dict[str, str] = {}

        columns = QHBoxLayout()
        for level in self.levels:
            vbox = QVBoxLayout()
            vbox.addWidget(QLabel(level.upper()))
            lw = QListWidget()
            lw.setObjectName(level)
            lw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            lw.setDragEnabled(True)
            lw.setAcceptDrops(True)
            lw.setDropIndicatorShown(True)
            lw.setDefaultDropAction(Qt.DropAction.MoveAction)
            self.lists[level] = lw

            for pid in getattr(roster, level):
                player = players.get(pid)
                if not player:
                    continue
                item = QListWidgetItem(f"{player.first_name} {player.last_name}")
                item.setData(Qt.ItemDataRole.UserRole, pid)
                lw.addItem(item)
                originals[pid] = level

            vbox.addWidget(lw)
            columns.addLayout(vbox)

        self.original_levels = originals

        move_btn = QPushButton("Reassign")
        move_btn.clicked.connect(self._apply_moves)

        layout = QVBoxLayout(self)
        layout.addLayout(columns)
        layout.addWidget(move_btn)

        def _calc_height(lw: QListWidget) -> int:
            row = lw.sizeHintForRow(0) if lw.count() else 20
            return row * max(lw.count(), 1) + 80

        height = max(_calc_height(lw) for lw in self.lists.values())
        self.resize(600, height)

    def _apply_moves(self) -> None:
        moved = False
        for dest_level, lw in self.lists.items():
            for i in range(lw.count()):
                item = lw.item(i)
                pid = item.data(Qt.ItemDataRole.UserRole)
                current = self.original_levels.get(pid)
                if current and current != dest_level:
                    try:
                        move_player_between_rosters(pid, self.roster, current, dest_level)
                        self.original_levels[pid] = dest_level
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
