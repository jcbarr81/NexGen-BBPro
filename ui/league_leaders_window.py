from __future__ import annotations

from typing import Iterable, List, Tuple

from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from models.base_player import BasePlayer


class LeagueLeadersWindow(QDialog):
    """Dialog showing leaders in common statistical categories."""

    def __init__(
        self,
        players: Iterable[BasePlayer],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("League Leaders")
        if callable(getattr(self, "resize", None)):
            self.resize(1000, 600)

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        layout.addWidget(self.table)

        player_list = list(players)
        rows = self._gather_leaders(player_list)

        self.table.setRowCount(len(rows))
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Category", "Player", "Value"])
        for row, (cat, name, value) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(cat))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem(value))
        self.table.setSortingEnabled(True)


    # ------------------------------------------------------------------
    def _gather_leaders(
        self, players: List[BasePlayer]
    ) -> List[Tuple[str, str, str]]:
        categories = [
            ("AVG", "avg", False, False),
            ("HR", "hr", True, False),
            ("RBI", "rbi", True, False),
            ("ERA", "era", False, True),
            ("SO", "so", True, True),
        ]
        rows: List[Tuple[str, str, str]] = []
        for label, key, high, pitcher_only in categories:
            candidates = [
                p
                for p in players
                if getattr(p, "is_pitcher", False) == pitcher_only
                and key in (getattr(p, "season_stats", {}) or {})
            ]
            if not candidates:
                continue
            if high:
                best = max(
                    candidates, key=lambda p: p.season_stats.get(key, 0)
                )
            else:
                best = min(
                    candidates,
                    key=lambda p: p.season_stats.get(key, float("inf")),
                )
            value = best.season_stats.get(key, 0)
            name = (
                f"{getattr(best, 'first_name', '')} "
                f"{getattr(best, 'last_name', '')}"
            ).strip()
            rows.append((label, name, str(value)))
        return rows
