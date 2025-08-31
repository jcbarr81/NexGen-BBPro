from __future__ import annotations

"""Dialog allowing owners to reassign players between roster levels."""

from typing import Dict, List
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QInputDialog,
    QMessageBox,
)

from models.base_player import BasePlayer
from models.roster import Roster
from utils.roster_loader import save_roster


class ReassignPlayersDialog(QDialog):
    """Dialog for reassigning players to different roster levels."""

    levels = ("act", "aaa", "low")

    def __init__(self, players: Dict[str, BasePlayer], roster: Roster, parent=None):
        super().__init__(parent)
        self.players = players
        self.roster = roster

        self.setWindowTitle("Reassign Players")

        self.lists: Dict[str, QListWidget] = {}
        self.labels: Dict[str, QLabel] = {}
        self.max_counts: Dict[str, int] = {"act": 25, "aaa": 15, "low": 10}

        columns = QHBoxLayout()
        for level in self.levels:
            vbox = QVBoxLayout()
            label = QLabel()
            vbox.addWidget(label)
            self.labels[level] = label
            lw = QListWidget()
            lw.setObjectName(level)
            lw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            lw.setDragEnabled(True)
            lw.setAcceptDrops(True)
            lw.setDropIndicatorShown(True)
            lw.setDefaultDropAction(Qt.DropAction.MoveAction)
            self.lists[level] = lw

            for pid in getattr(self.roster, level):
                player = players.get(pid)
                if not player:
                    continue
                age = self._calculate_age(player.birthdate)
                text = (
                    f"{player.first_name} {player.last_name} "
                    f"({age}) - {player.primary_position}"
                )
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, pid)
                lw.addItem(item)

            vbox.addWidget(lw)
            columns.addLayout(vbox)

        move_btn = QPushButton("Reassign")
        move_btn.clicked.connect(self._apply_moves)

        save_btn = QPushButton("Save Roster", objectName="Primary")
        save_btn.clicked.connect(self._save_roster)

        layout = QVBoxLayout(self)
        layout.addLayout(columns)
        layout.addWidget(move_btn)
        layout.addWidget(save_btn)

        def _calc_height(lw: QListWidget) -> int:
            row = lw.sizeHintForRow(0) if lw.count() else 20
            return row * max(lw.count(), 1) + 80

        height = max(_calc_height(lw) for lw in self.lists.values())
        self.resize(600, height)
        self._update_counts()

    def _calculate_age(self, birthdate_str: str):
        try:
            birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            return today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )
        except Exception:
            return "?"

    def _apply_moves(self) -> None:
        selected_item = None
        from_level = None
        for level, lw in self.lists.items():
            items = lw.selectedItems()
            if items:
                selected_item = items[0]
                from_level = level
                break

        if not selected_item or not from_level:
            QMessageBox.warning(self, "Reassign Player", "Select a player first.")
            return

        pid = selected_item.data(Qt.ItemDataRole.UserRole)
        options = [lvl.upper() for lvl in self.levels if lvl != from_level]
        choice, ok = QInputDialog.getItem(
            self, "Reassign Player", "Move to:", options, 0, False
        )
        if not ok:
            return
        to_level = choice.lower()

        try:
            self.roster.move_player(pid, from_level, to_level)
        except ValueError:
            QMessageBox.critical(
                self, "Error", f"Failed to move player {pid} from {from_level}"
            )
            return

        self.lists[from_level].takeItem(self.lists[from_level].row(selected_item))
        self.lists[to_level].addItem(selected_item)

        self.lists[from_level].update()
        self.lists[to_level].update()
        self._update_counts()
        self.update()

    def _update_counts(self) -> None:
        """Refresh roster counts displayed above each column."""
        for level, label in self.labels.items():
            count = len(getattr(self.roster, level))
            max_count = self.max_counts.get(level)
            label.setText(f"{level.upper()} ({count}/{max_count})")

    def _validate_roster(self) -> List[str]:
        """Return a list of roster rule violations."""
        errors: List[str] = []
        if len(self.roster.act) > self.max_counts["act"]:
            errors.append("Active roster exceeds 25 players.")

        pos_players = [
            pid
            for pid in self.roster.act
            if (player := self.players.get(pid)) and player.primary_position != "P"
        ]
        if len(pos_players) < 11:
            errors.append("Active roster must have at least 11 position players.")

        if len(self.roster.aaa) > self.max_counts["aaa"]:
            errors.append("AAA roster exceeds 15 players.")

        if len(self.roster.low) > self.max_counts["low"]:
            errors.append("Low roster exceeds 10 players.")

        return errors

    def _save_roster(self) -> None:
        """Persist roster changes to disk after validating rules."""
        errors = self._validate_roster()
        if errors:
            QMessageBox.warning(self, "Roster Violations", "\n".join(errors))
            return

        try:
            save_roster(self.roster.team_id, self.roster)
        except Exception as exc:  # pragma: no cover - UI feedback
            QMessageBox.critical(self, "Save Failed", str(exc))
            return

        QMessageBox.information(self, "Roster Saved", "Roster saved successfully.")

