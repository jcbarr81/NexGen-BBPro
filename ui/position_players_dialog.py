"""Retro-style dialog showing a team's position players roster.

This refactors the previous tabbed dialog into a single table that mimics the
retro roster mock-up found in ``samples/Roster-Sample.py``. Sample data is
replaced with the real data for the team being viewed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from PyQt6 import QtCore, QtGui, QtWidgets

from ui.player_profile_dialog import PlayerProfileDialog

from models.base_player import BasePlayer
from models.roster import Roster
from utils.pitcher_role import get_role


# ---------------------------------------------------------------------------
# Retro colour palette
RETRO_GREEN = "#0f3b19"
RETRO_GREEN_DARK = "#0b2a12"
RETRO_GREEN_TABLE = "#164a22"
RETRO_BEIGE = "#d2ba8f"
RETRO_YELLOW = "#ffd34d"
RETRO_TEXT = "#ffffff"
RETRO_CYAN = "#6ce5ff"
RETRO_BORDER = "#3a5f3a"

COLUMNS = [
    "NO.",
    "Player Name",
    "SLOT",
    "POSN",
    "B",
    "CH",
    "PH",
    "SP",
    "FA",
    "AS",
]


class NumberDelegate(QtWidgets.QStyledItemDelegate):
    """Right align numeric cells and tint them retro cyan."""

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        header = index.model().headerData(
            index.column(), QtCore.Qt.Orientation.Horizontal
        )
        is_numeric_col = header in {"NO.", "CH", "PH", "SP", "FA", "AS"}
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if is_numeric_col:
            opt.displayAlignment = (
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            opt.palette.setColor(
                QtGui.QPalette.ColorRole.Text, QtGui.QColor(RETRO_CYAN)
            )
        else:
            opt.displayAlignment = (
                QtCore.Qt.AlignmentFlag.AlignLeft
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            opt.palette.setColor(
                QtGui.QPalette.ColorRole.Text, QtGui.QColor(RETRO_TEXT)
            )
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawControl(
            QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget
        )


class RetroHeader(QtWidgets.QWidget):
    """Header area displaying team name and subheader strip."""

    def __init__(self, team_id: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            f"background:{RETRO_GREEN}; border-bottom: 1px solid {RETRO_BORDER};"
        )

        title = QtWidgets.QLabel(f"Team Roster — {team_id}")
        title_font = QtGui.QFont("Segoe UI", 16, QtGui.QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setStyleSheet("color: #ff6b6b; letter-spacing: 0.5px;")

        strip = QtWidgets.QFrame()
        strip.setStyleSheet(
            f"background:{RETRO_GREEN_DARK}; border: 1px solid {RETRO_BORDER};"
        )
        strip_layout = QtWidgets.QHBoxLayout(strip)
        strip_layout.setContentsMargins(10, 6, 10, 6)
        strip_layout.setSpacing(8)

        team_line = QtWidgets.QLabel(team_id)
        team_line.setStyleSheet(f"color:{RETRO_YELLOW}; font-weight:600;")
        season = QtWidgets.QLabel("Season data")
        season.setStyleSheet(f"color:{RETRO_YELLOW};")

        arrow = QtWidgets.QLabel("▲")
        arrow.setStyleSheet(f"color:{RETRO_YELLOW}; font-weight:700;")
        arrow.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        strip_layout.addWidget(team_line, 1)
        strip_layout.addWidget(season)
        strip_layout.addStretch(1)
        strip_layout.addWidget(arrow)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)
        lay.addWidget(title)
        lay.addWidget(strip)


class RosterTable(QtWidgets.QTableWidget):
    """Table displaying the team's position players."""

    def __init__(self, rows: List[List], parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setRowCount(len(rows))

        for r, row in enumerate(rows):
            # The player ID is stored as a hidden element at the end of the row.
            *data, pid = row
            for c, val in enumerate(data):
                item = QtWidgets.QTableWidgetItem(str(val))
                if COLUMNS[c] in {"NO.", "CH", "PH", "SP", "FA", "AS"}:
                    item.setData(QtCore.Qt.ItemDataRole.DisplayRole, int(val))
                if c == 0:  # store player id in first column
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, pid)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.setItem(r, c, item)

        widths = [50, 220, 60, 60, 40, 60, 60, 60, 60, 60]
        for i, w in enumerate(widths):
            self.setColumnWidth(i, w)

        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.setAlternatingRowColors(False)

        self.setStyleSheet(
            f"QTableWidget {{ background:{RETRO_GREEN_TABLE}; color:{RETRO_TEXT};"
            f" gridline-color:{RETRO_BORDER}; selection-background-color:#245b2b;"
            f" selection-color:{RETRO_TEXT}; font: 12px 'Segoe UI'; }}"
            f"QHeaderView::section {{ background:{RETRO_GREEN}; color:{RETRO_TEXT};"
            f" border: 1px solid {RETRO_BORDER}; font-weight:600; }}"
            f"QScrollBar:vertical {{ background:{RETRO_GREEN_DARK}; width: 12px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background:{RETRO_BEIGE}; min-height: 24px; }}"
        )

        delegate = NumberDelegate(self)
        self.setItemDelegate(delegate)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )


class StatusFooter(QtWidgets.QStatusBar):
    """Simple status bar matching the retro palette."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{RETRO_GREEN}; color:{RETRO_TEXT};"
            f" border-top: 1px solid {RETRO_BORDER};"
        )
        self.setSizeGripEnabled(False)

        left = QtWidgets.QLabel("NexGen-BBpro")
        right = QtWidgets.QLabel("JBARR 2025")
        right.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        container = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(container)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.addWidget(left)
        lay.addWidget(spacer)
        lay.addWidget(right)

        self.addPermanentWidget(container, 1)


class PositionPlayersDialog(QtWidgets.QDialog):
    """Display all position players in a retro roster table."""

    def __init__(
        self,
        players: Dict[str, BasePlayer],
        roster: Roster,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self.players = players
        self.roster = roster

        self.setWindowTitle("Position Players")
        self.resize(930, 560)
        self._apply_global_palette()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.header = RetroHeader(roster.team_id)
        layout.addWidget(self.header)

        rows = self._build_rows()
        self.table = RosterTable(rows)
        self.table.itemDoubleClicked.connect(self._open_player_profile)
        layout.addWidget(self.table, 1)

        self.statusbar = StatusFooter()
        layout.addWidget(self.statusbar)

    # ------------------------------------------------------------------
    # Data helpers
    def _build_rows(self) -> List[List]:
        """Create table rows for all non-pitchers across roster levels."""

        rows: List[List] = []
        seq = 1
        for slot, ids in (
            ("ACT", self.roster.act),
            ("AAA", self.roster.aaa),
            ("LOW", self.roster.low),
        ):
            for pid in ids:
                p = self.players.get(pid)
                if not p or get_role(p):
                    continue
                rows.append(
                    [
                        seq,
                        f"{p.last_name}, {p.first_name}",
                        slot,
                        p.primary_position,
                        p.bats,
                        getattr(p, "ch", 0),
                        getattr(p, "ph", 0),
                        getattr(p, "sp", 0),
                        getattr(p, "fa", 0),
                        getattr(p, "arm", 0),
                        pid,
                    ]
                )
                seq += 1
        return rows

    # ------------------------------------------------------------------
    # Helpers for tests and compatibility
    def _make_player_item(self, p: BasePlayer) -> QtWidgets.QListWidgetItem:
        """Format a player entry similar to OwnerDashboard._make_player_item."""

        age = self._calculate_age(p.birthdate)
        role = get_role(p)
        if role:
            core = (
                f"AS:{getattr(p, 'arm', 0)} EN:{getattr(p, 'endurance', 0)} "
                f"CO:{getattr(p, 'control', 0)}"
            )
        else:
            core = (
                f"CH:{getattr(p, 'ch', 0)} PH:{getattr(p, 'ph', 0)} "
                f"SP:{getattr(p, 'sp', 0)}"
            )
        label = (
            f"{p.first_name} {p.last_name} ({age}) - {role or p.primary_position} | {core}"
        )
        item = QtWidgets.QListWidgetItem(label)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, p.player_id)
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
    def _open_player_profile(self, item: QtWidgets.QTableWidgetItem):
        """Open the player profile dialog for the selected table row."""

        row = item.row()
        pid_item = self.table.item(row, 0)
        if not pid_item:
            return
        pid = pid_item.data(QtCore.Qt.ItemDataRole.UserRole)
        player = self.players.get(pid)
        if not player:
            return
        PlayerProfileDialog(player, self).exec()

    # ------------------------------------------------------------------
    # Palette helpers
    def _apply_global_palette(self) -> None:
        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(RETRO_GREEN))
        pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(RETRO_GREEN_TABLE))
        pal.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(RETRO_TEXT))
        pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(RETRO_BEIGE))
        pal.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#222"))
        self.setPalette(pal)
        self.setStyleSheet(
            f"QDialog {{ background:{RETRO_GREEN}; }}"
            f"QPushButton {{ background:{RETRO_BEIGE}; color:#222; }}"
        )

