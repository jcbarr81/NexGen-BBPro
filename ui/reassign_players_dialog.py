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
from ui.player_profile_dialog import PlayerProfileDialog
from utils.roster_loader import save_roster
from utils.roster_validation import missing_positions
from services.roster_moves import cut_player as cut_player_service


class RosterListWidget(QListWidget):
    """List widget that syncs roster data on drag and drop."""

    def __init__(self, level: str, dialog: "ReassignPlayersDialog") -> None:
        super().__init__()
        self.level = level
        self.dialog = dialog
        self.setObjectName(level)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        """Handle drag-and-drop moves and refresh counts."""
        super().dropEvent(event)
        self.dialog._sync_roster_from_lists()
        self.dialog._update_counts()

class ReassignPlayersDialog(QDialog):
    """Dialog for reassigning players to different roster levels."""

    levels = ("act", "aaa", "low")

    def __init__(self, players: Dict[str, BasePlayer], roster: Roster, parent=None):
        super().__init__(parent)
        self.players = players
        self.roster = roster

        self.setWindowTitle("Reassign Players")

        self.lists: Dict[str, RosterListWidget] = {}
        self.labels: Dict[str, QLabel] = {}
        self.max_counts: Dict[str, int] = {"act": 25, "aaa": 15, "low": 10}

        columns = QHBoxLayout()
        for level in self.levels:
            vbox = QVBoxLayout()
            label = QLabel()
            vbox.addWidget(label)
            self.labels[level] = label
            lw = RosterListWidget(level, self)
            lw.itemDoubleClicked.connect(self._open_player_profile)
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
        cut_btn = QPushButton("Cut Selected Player(s)")
        cut_btn.clicked.connect(self._cut_selected_player)

        save_btn = QPushButton("Save Roster", objectName="Primary")
        save_btn.clicked.connect(self._save_roster)

        layout = QVBoxLayout(self)
        info = QLabel(
            "Drag players between lists or multi-select (Ctrl/Shift) and "
            "click Reassign."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addLayout(columns)
        layout.addWidget(move_btn)
        layout.addWidget(cut_btn)

        note = QLabel(
            "Changes will not be saved until you click 'Save Roster'."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(save_btn)

        def _calc_height(lw: QListWidget) -> int:
            row = lw.sizeHintForRow(0) if lw.count() else 20
            return row * max(lw.count(), 1) + 80

        height = max(_calc_height(lw) for lw in self.lists.values())
        self.resize(900, height)
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

    def _open_player_profile(self, item: QListWidgetItem) -> None:
        """Open the player profile dialog for the selected player."""
        pid = item.data(Qt.ItemDataRole.UserRole)
        player = self.players.get(pid)
        if not player:
            return
        PlayerProfileDialog(player, self).exec()

    def _resolve_selection(
        self, dialog_title: str
    ) -> tuple[str, List[QListWidgetItem]] | None:
        """Return selected items grouped by roster level or warn if invalid."""
        selected = [
            (level, lw.selectedItems())
            for level, lw in self.lists.items()
            if lw.selectedItems()
        ]
        if not selected:
            QMessageBox.warning(
                self,
                dialog_title,
                "Select at least one player first.",
            )
            return None
        if len(selected) > 1:
            QMessageBox.warning(
                self,
                dialog_title,
                "Select players from only one roster column.",
            )
            return None
        level, items = selected[0]
        return level, list(items)

    def _apply_moves(self) -> None:
        selection = self._resolve_selection("Reassign Players")
        if not selection:
            return
        from_level, items = selection
        if not items:
            return

        selected = []
        for item in items:
            pid = item.data(Qt.ItemDataRole.UserRole)
            player = self.players.get(pid)
            age = self._calculate_age(player.birthdate) if player else None
            selected.append((item, pid, player, age))

        options: List[str] = []
        for level in self.levels:
            if level == from_level:
                continue
            if level == "low":
                if any(isinstance(age, int) and age >= 27 for _, _, _, age in selected):
                    continue
            options.append(level.upper())

        if not options:
            QMessageBox.warning(
                self, "Reassign Players", "No valid destination rosters."
            )
            return

        choice, ok = QInputDialog.getItem(
            self, "Reassign Players", "Move to:", options, 0, False
        )
        if not ok:
            return
        to_level = choice.lower()

        source_list = self.lists[from_level]
        target_list = self.lists[to_level]
        moved: List[str] = []

        for item, pid, _player, _age in selected:
            try:
                self.roster.move_player(pid, from_level, to_level)
            except ValueError:
                QMessageBox.critical(
                    self,
                    "Reassign Players",
                    f"Failed to move player {pid} from {from_level.upper()}.",
                )
                continue

            row = source_list.row(item)
            moved_item = source_list.takeItem(row)
            target_list.addItem(moved_item)
            moved.append(pid)

        if not moved:
            return

        source_list.update()
        target_list.update()
        self._sync_roster_from_lists()
        self._update_counts()
        self.update()

    def _cut_selected_player(self) -> None:
        selection = self._resolve_selection("Cut Players")
        if not selection:
            return
        from_level, items = selection
        if not items:
            return

        selected = []
        for item in items:
            pid = item.data(Qt.ItemDataRole.UserRole)
            player = self.players.get(pid)
            name = f"{player.first_name} {player.last_name}" if player else pid
            selected.append((item, pid, name))

        if len(selected) == 1:
            prompt = f"Release {selected[0][2]} from the organization?"
        else:
            names = "\n".join(f"- {name}" for _, _, name in selected)
            prompt = (
                "Release the following players from the organization?\n\n"
                f"{names}"
            )

        reply = QMessageBox.question(
            self,
            "Cut Players",
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._sync_roster_from_lists()
        source_list = self.lists[from_level]
        successful: List[str] = []
        errors: List[str] = []

        for item, pid, name in selected:
            try:
                updated_roster, _removed_level = cut_player_service(
                    self.roster.team_id, pid, self.roster
                )
                self.roster = updated_roster
            except ValueError as exc:
                errors.append(str(exc))
                continue
            except Exception as exc:
                errors.append(f"Failed to cut {name}: {exc}")
                continue

            row = source_list.row(item)
            source_list.takeItem(row)
            successful.append(name)

        if successful:
            self._sync_roster_from_lists()
            self._update_counts()
            self.update()
            if len(successful) == 1:
                QMessageBox.information(
                    self, "Cut Players", f"{successful[0]} was released."
                )
            else:
                released = ", ".join(successful)
                QMessageBox.information(
                    self,
                    "Cut Players",
                    f"Released {len(successful)} players: {released}.",
                )

        if errors:
            QMessageBox.warning(self, "Cut Players", "\n".join(errors))


    def _sync_roster_from_lists(self) -> None:
        """Sync internal roster lists with the GUI widgets."""
        for level, lw in self.lists.items():
            ids: List[str] = []
            for i in range(lw.count()):
                item = lw.item(i)
                pid = item.data(Qt.ItemDataRole.UserRole)
                ids.append(pid)
            setattr(self.roster, level, ids)

    def _update_counts(self) -> None:
        """Refresh roster counts displayed above each column."""
        for level, label in self.labels.items():
            count = self.lists[level].count()
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

        # Defensive coverage check: ensure every position can be fielded
        missing = missing_positions(self.roster, self.players)
        if missing:
            positions = ", ".join(missing)
            errors.append(f"Active roster lacks coverage for: {positions}.")

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

