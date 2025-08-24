from __future__ import annotations

from typing import Iterable, List

from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from models.team import Team
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

_TEAM_COLS: List[str] = ["g", "w", "l", "r", "ra"]


class LeagueStatsWindow(QDialog):
    """Dialog showing statistics for teams and players across the league."""

    def __init__(
        self,
        teams: Iterable[Team],
        players: Iterable[BasePlayer],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("League Statistics")
        if callable(getattr(self, "resize", None)):
            self.resize(1000, 600)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        team_list = list(teams)
        player_list = list(players)

        self.tabs.addTab(self._build_team_table(team_list), "Teams")
        batters = [p for p in player_list if not getattr(p, "is_pitcher", False)]
        pitchers = [p for p in player_list if getattr(p, "is_pitcher", False)]
        self.tabs.addTab(self._build_player_table(batters, _BATTING_COLS), "Batters")
        self.tabs.addTab(self._build_player_table(pitchers, _PITCHING_COLS), "Pitchers")

    # ------------------------------------------------------------------
    def _build_team_table(self, teams: List[Team]) -> QTableWidget:
        table = QTableWidget(len(teams), len(_TEAM_COLS) + 1)
        headers = ["Team"] + [c.upper() for c in _TEAM_COLS]
        table.setHorizontalHeaderLabels(headers)
        for row, team in enumerate(teams):
            name = f"{team.city} {team.name}".strip()
            table.setItem(row, 0, QTableWidgetItem(name))
            stats = getattr(team, "season_stats", {}) or {}
            for col, key in enumerate(_TEAM_COLS, start=1):
                table.setItem(row, col, QTableWidgetItem(str(stats.get(key, 0))))
        table.setSortingEnabled(True)
        return table

    def _build_player_table(
        self, players: Iterable[BasePlayer], columns: List[str]
    ) -> QTableWidget:
        players = list(players)
        table = QTableWidget(len(players), len(columns) + 1)
        headers = ["Name"] + [c.upper() for c in columns]
        table.setHorizontalHeaderLabels(headers)
        for row, player in enumerate(players):
            name = f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip()
            table.setItem(row, 0, QTableWidgetItem(name))
            stats = getattr(player, "season_stats", {}) or {}
            for col, key in enumerate(columns, start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, QTableWidgetItem(str(value)))
        table.setSortingEnabled(True)
        return table
