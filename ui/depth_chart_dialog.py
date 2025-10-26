from __future__ import annotations

"""Dialog for editing position depth charts for a team."""

from typing import Dict, List

try:  # pragma: no cover - PyQt stubs for tests
    from PyQt6.QtWidgets import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QGridLayout,
        QLabel,
        QMessageBox,
        QVBoxLayout,
        QWidget,
    )
except Exception:  # pragma: no cover
    class _Signal:
        def connect(self, *_args, **_kwargs):
            return None

    class QWidget:  # type: ignore[too-many-ancestors]
        def __init__(self, *args, **kwargs):
            pass

    class QDialog(QWidget):
        def reject(self):
            pass

    class QLabel(QWidget):
        def __init__(self, text="", *_, **__):
            self._text = text

        def setText(self, text):
            self._text = text

    class QComboBox(QWidget):
        def __init__(self, *_, **__):
            self._items: list[tuple[str, str]] = []
            self._index = 0

        def addItem(self, label, data=""):
            self._items.append((label, data))

        def findData(self, value):
            for idx, (_, data) in enumerate(self._items):
                if data == value:
                    return idx
            return -1

        def setCurrentIndex(self, idx):
            if 0 <= idx < len(self._items):
                self._index = idx

        def currentData(self):
            if 0 <= self._index < len(self._items):
                return self._items[self._index][1]
            return ""

    class QGridLayout:
        def __init__(self, *_, **__):
            pass

        def addWidget(self, *_, **__):
            pass

        def addLayout(self, *_, **__):
            pass

    class QVBoxLayout(QGridLayout):
        def __init__(self, *_args, **_kwargs):
            super().__init__()

    class QMessageBox:
        @staticmethod
        def information(*_, **__):
            pass

        @staticmethod
        def warning(*_, **__):
            pass

    class QDialogButtonBox(QWidget):
        class StandardButton:
            Save = 1
            Cancel = 2

        def __init__(self, *_a, **_k):
            self.accepted = _Signal()
            self.rejected = _Signal()

from utils.player_loader import load_players_from_csv
from utils.roster_loader import load_roster
from utils.depth_chart import (
    DEPTH_CHART_POSITIONS,
    depth_order_for_position,
    load_depth_chart,
    save_depth_chart,
)


class DepthChartDialog(QDialog):
    def __init__(self, dashboard):
        super().__init__(dashboard)
        self._dashboard = dashboard
        self.team_id = getattr(dashboard, "team_id", "")
        self.setWindowTitle(f"Depth Chart — {self.team_id}")
        self.resize(600, 420)
        self.players = {p.player_id: p for p in load_players_from_csv("data/players.csv")}
        self.roster = load_roster(self.team_id)
        try:
            self.chart = load_depth_chart(self.team_id)
        except Exception:
            self.chart = {}
        self._level_map = self._build_level_index()
        self._combo_map: Dict[tuple[str, int], QComboBox] = {}
        self._build_ui()
        self._apply_existing_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Position"), 0, 0)
        for idx, label in enumerate(["Starter", "1st Backup", "2nd Backup"], start=1):
            grid.addWidget(QLabel(label), 0, idx)
        for row, pos in enumerate(DEPTH_CHART_POSITIONS, start=1):
            grid.addWidget(QLabel(pos), row, 0)
            for slot in range(3):
                combo = QComboBox()
                self._populate_combo(combo, pos)
                grid.addWidget(combo, row, slot + 1)
                self._combo_map[(pos, slot)] = combo
        root.addLayout(grid)
        self.status_label = QLabel()
        root.addWidget(self.status_label)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        try:
            buttons.accepted.connect(self._save)
            buttons.rejected.connect(self.reject)
        except Exception:
            pass
        root.addWidget(buttons)

    def _build_level_index(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for level, group in (
            ("ACT", self.roster.act),
            ("AAA", self.roster.aaa),
            ("LOW", self.roster.low),
            ("DL", self.roster.dl),
            ("IR", self.roster.ir),
        ):
            for pid in group:
                mapping[pid] = level
        return mapping

    def _player_label(self, pid: str) -> str:
        player = self.players.get(pid)
        if player is None:
            return pid
        name = f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip()
        pos = getattr(player, "primary_position", "")
        level = self._level_map.get(pid, "")
        suffix = f" ({level})" if level else ""
        return f"{name} - {pos}{suffix}"

    def _eligible_players(self, position: str) -> List[str]:
        pos = position.upper()
        ids = (
            list(self.roster.act)
            + list(self.roster.aaa)
            + list(self.roster.low)
            + list(self.roster.dl)
            + list(self.roster.ir)
        )
        def can_play(pid: str) -> bool:
            player = self.players.get(pid)
            if player is None:
                return False
            if getattr(player, "is_pitcher", False):
                return False
            primary = str(getattr(player, "primary_position", "")).upper()
            if pos == "DH":
                return True
            if primary == pos:
                return True
            for other in getattr(player, "other_positions", []) or []:
                if str(other).upper() == pos:
                    return True
            return False

        return [pid for pid in ids if can_play(pid)]

    def _populate_combo(self, combo: QComboBox, position: str) -> None:
        combo.addItem("— None —", "")
        for pid in self._eligible_players(position):
            combo.addItem(self._player_label(pid), pid)

    def _apply_existing_values(self) -> None:
        for pos in DEPTH_CHART_POSITIONS:
            entries = depth_order_for_position(self.chart, pos)
            for slot in range(3):
                combo = self._combo_map.get((pos, slot))
                if combo is None:
                    continue
                pid = entries[slot] if slot < len(entries) else ""
                if not pid:
                    combo.setCurrentIndex(0)
                    continue
                idx = combo.findData(pid)
                if idx == -1:
                    combo.addItem(self._player_label(pid), pid)
                    idx = combo.findData(pid)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    def _save(self) -> None:
        result: Dict[str, List[str]] = {pos: [] for pos in DEPTH_CHART_POSITIONS}
        for pos in DEPTH_CHART_POSITIONS:
            seen: set[str] = set()
            for slot in range(3):
                combo = self._combo_map.get((pos, slot))
                if combo is None:
                    continue
                pid = combo.currentData() or ""
                pid = str(pid).strip()
                if pid and pid not in seen:
                    seen.add(pid)
                    result[pos].append(pid)
        try:
            save_depth_chart(self.team_id, result)
        except Exception as exc:
            QMessageBox.warning(self, "Depth Chart", f"Failed to save depth chart: {exc}")
            return
        self.status_label.setText("Saved.")
        QMessageBox.information(self, "Depth Chart", "Depth chart saved.")


__all__ = ["DepthChartDialog"]
