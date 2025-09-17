from __future__ import annotations

from typing import Iterable, List, Any, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from models.team import Team
from models.base_player import BasePlayer
from utils.stats_persistence import load_stats
from .components import Card, section_title

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
    "sb",
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


class NumericItem(QTableWidgetItem):
    """Table item that sorts numerically when possible."""

    def __init__(self, value: Any, *, align_left: bool = False) -> None:
        super().__init__()
        alignment = Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignRight
        self.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)

        if isinstance(value, (int, float)):
            self.setData(Qt.ItemDataRole.DisplayRole, f"{value:.3f}" if isinstance(value, float) else str(value))
            self.setData(Qt.ItemDataRole.EditRole, float(value))
            return

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            self.setData(Qt.ItemDataRole.DisplayRole, str(value))
        else:
            self.setData(Qt.ItemDataRole.DisplayRole, f"{numeric:.3f}")
            self.setData(Qt.ItemDataRole.EditRole, numeric)


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
            self.resize(1000, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        team_list = list(teams)
        player_list = list(players)

        stats = load_stats()
        team_stats = stats.get("teams", {})
        for team in team_list:
            if not getattr(team, "season_stats", None) and team.team_id in team_stats:
                team.season_stats = team_stats[team.team_id]
        player_stats = stats.get("players", {})
        for player in player_list:
            pid = getattr(player, "player_id", None)
            if pid and not getattr(player, "season_stats", None):
                if pid in player_stats:
                    player.season_stats = player_stats[pid]

        self.tabs.addTab(self._build_team_table(team_list), "Teams")
        batters = [p for p in player_list if not getattr(p, "is_pitcher", False)]
        pitchers = [p for p in player_list if getattr(p, "is_pitcher", False)]
        self.tabs.addTab(self._build_player_table(batters, _BATTING_COLS, title="League Batting"), "Batters")
        self.tabs.addTab(self._build_player_table(pitchers, _PITCHING_COLS, title="League Pitching"), "Pitchers")

    # ------------------------------------------------------------------
    def _build_team_table(self, teams: List[Team]) -> Card:
        card = Card()
        card.layout().addWidget(section_title("Team Totals"))

        table = QTableWidget(len(teams), len(_TEAM_COLS) + 1)
        headers = ["Team"] + [c.upper() for c in _TEAM_COLS]
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row, team in enumerate(teams):
            name = f"{team.city} {team.name}".strip()
            table.setItem(row, 0, NumericItem(name, align_left=True))
            stats = getattr(team, "season_stats", {}) or {}
            for col, key in enumerate(_TEAM_COLS, start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, NumericItem(value))

        table.setSortingEnabled(True)
        card.layout().addWidget(table)
        return card

    def _build_player_table(
        self,
        players: Iterable[BasePlayer],
        columns: List[str],
        *,
        title: str,
    ) -> Card:
        players = list(players)
        card = Card()
        card.layout().addWidget(section_title(title))

        table = QTableWidget(len(players), len(columns) + 1)
        headers = ["Name"] + [c.upper() for c in columns]
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        is_pitching_view = columns is _PITCHING_COLS
        for row, player in enumerate(players):
            name = f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip()
            table.setItem(row, 0, NumericItem(name, align_left=True))
            stats = getattr(player, "season_stats", {}) or {}
            if is_pitching_view:
                stats = self._normalize_pitching_stats(stats)
            else:
                stats = self._normalize_batting_stats(stats)
            for col, key in enumerate(columns, start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, NumericItem(value))

        table.setSortingEnabled(True)
        card.layout().addWidget(table)
        return card

    # ------------------------------------------------------------------
    def _normalize_batting_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(stats)
        if "b2" in data and "2b" not in data:
            data["2b"] = data.get("b2", 0)
        if "b3" in data and "3b" not in data:
            data["3b"] = data.get("b3", 0)
        return data

    def _normalize_pitching_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(stats)
        outs = data.get("outs")
        if outs is not None and "ip" not in data:
            data["ip"] = outs / 3
        ip = data.get("ip", 0)
        if ip:
            er = data.get("er", 0)
            data.setdefault("era", (er * 9) / ip if ip else 0.0)
            walks_hits = data.get("bb", 0) + data.get("h", 0)
            data.setdefault("whip", walks_hits / ip if ip else 0.0)
        data.setdefault("w", data.get("wins", data.get("w", 0)))
        data.setdefault("l", data.get("losses", data.get("l", 0)))
        return data
