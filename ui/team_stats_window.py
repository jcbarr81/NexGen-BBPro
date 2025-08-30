from __future__ import annotations

from typing import Dict, Iterable, List

from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from models.team import Team
from models.roster import Roster
from models.base_player import BasePlayer


_BATTING_COLS: List[str] = [
    "g",
    "ab",
    "r",
    "h",
    "2b",
    "3b",
    "hr",
    "rbi",
    "bb",
    "so",
    "avg",
    "obp",
    "slg",
]

_PITCHING_COLS: List[str] = [
    "w",
    "l",
    "era",
    "g",
    "gs",
    "sv",
    "ip",
    "h",
    "er",
    "bb",
    "so",
    "whip",
]


class TeamStatsWindow(QDialog):
    """Dialog showing player and team statistics for a single team."""

    def __init__(
        self,
        team: Team,
        players: Dict[str, BasePlayer],
        roster: Roster,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.team = team
        self.players = players
        self.roster = roster

        self.setWindowTitle("Team Statistics")
        if callable(getattr(self, "resize", None)):
            self.resize(1000, 600)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        batter_ids = [
            pid
            for pid in roster.act
            if pid in players
            and not getattr(players[pid], "is_pitcher", False)
        ]
        pitcher_ids = [
            pid
            for pid in roster.act
            if pid in players
            and getattr(players[pid], "is_pitcher", False)
        ]

        batters = [players[pid] for pid in batter_ids]
        pitchers = [players[pid] for pid in pitcher_ids]

        self.tabs.addTab(
            self._build_player_table(batters, _BATTING_COLS),
            "Batting",
        )
        self.tabs.addTab(
            self._build_player_table(pitchers, _PITCHING_COLS),
            "Pitching",
        )
        self.tabs.addTab(self._build_team_table(team.season_stats), "Team")

    # ------------------------------------------------------------------
    def _build_player_table(
        self, players: Iterable[BasePlayer], columns: List[str]
    ) -> QTableWidget:
        players = list(players)
        table = QTableWidget(len(players), len(columns) + 1)
        headers = ["Name"] + [c.upper() for c in columns]
        table.setHorizontalHeaderLabels(headers)
        for row, player in enumerate(players):
            name = (
                f"{getattr(player, 'first_name', '')} "
                f"{getattr(player, 'last_name', '')}"
            ).strip()
            table.setItem(row, 0, QTableWidgetItem(name))
            stats = getattr(player, "season_stats", {}) or {}
            for col, key in enumerate(columns, start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, QTableWidgetItem(str(value)))
        table.setSortingEnabled(True)
        return table


    def _build_team_table(self, stats: Dict[str, float]) -> QTableWidget:
        items = sorted(stats.items())
        table = QTableWidget(len(items), 2)
        table.setHorizontalHeaderLabels(["Stat", "Value"])
        for row, (key, value) in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(str(key)))
            table.setItem(row, 1, QTableWidgetItem(str(value)))
        table.setSortingEnabled(True)
        return table
