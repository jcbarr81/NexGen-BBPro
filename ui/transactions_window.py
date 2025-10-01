from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from services.transaction_log import load_transactions


class TransactionsWindow(QDialog):
    """Dialog displaying recent roster transactions with simple filters."""

    COLUMNS = [
        "Timestamp",
        "Season Date",
        "Team",
        "Player",
        "Action",
        "Movement",
        "Counterparty",
        "Details",
    ]

    ACTION_FILTERS = [
        ("All", None),
        ("Draft", {"draft"}),
        ("Cut", {"cut"}),
        ("Trade In", {"trade_in"}),
        ("Trade Out", {"trade_out"}),
    ]

    def __init__(self, team_id: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._initial_team = team_id
        self.setWindowTitle("Transactions")
        self.resize(900, 420)

        layout = QVBoxLayout(self)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Team:"))
        self.team_box = QComboBox()
        filters.addWidget(self.team_box)
        filters.addWidget(QLabel("Action:"))
        self.action_box = QComboBox()
        for label, _ in self.ACTION_FILTERS:
            self.action_box.addItem(label)
        filters.addStretch(1)
        refresh_btn = QPushButton("Refresh")
        filters.addWidget(refresh_btn)
        layout.addLayout(filters)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        refresh_btn.clicked.connect(self._reload)
        self.team_box.currentIndexChanged.connect(self._reload)
        self.action_box.currentIndexChanged.connect(self._reload)

        self._populate_team_filter()
        self._reload()

    def _populate_team_filter(self) -> None:
        rows = load_transactions()
        team_ids = sorted({row.get("team_id", "") for row in rows if row.get("team_id")})
        self.team_box.blockSignals(True)
        self.team_box.clear()
        self.team_box.addItem("All Teams", None)
        for tid in team_ids:
            self.team_box.addItem(tid, tid)
        if self._initial_team and self._initial_team in team_ids:
            index = self.team_box.findData(self._initial_team)
            if index >= 0:
                self.team_box.setCurrentIndex(index)
        self.team_box.blockSignals(False)

    def _reload(self) -> None:
        team_value = self.team_box.currentData()
        action_idx = max(self.action_box.currentIndex(), 0)
        _, action_filter = self.ACTION_FILTERS[action_idx]

        rows = load_transactions(
            team_id=team_value,
            actions=action_filter,
        )
        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            movement = ""
            if row.get("from_level") or row.get("to_level"):
                movement = f"{row.get('from_level', '')} -> {row.get('to_level', '')}"
            values = [
                row.get("timestamp", ""),
                row.get("season_date", ""),
                row.get("team_id", ""),
                row.get("player_name", row.get("player_id", "")),
                row.get("action", "").replace("_", " ").title(),
                movement,
                row.get("counterparty", ""),
                row.get("details", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in (0, 1):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col, item)
        self.table.resizeColumnsToContents()


__all__ = ["TransactionsWindow"]
