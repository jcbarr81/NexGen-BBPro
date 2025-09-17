from __future__ import annotations

from typing import Dict, Iterable, List, Any

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
from models.roster import Roster
from models.base_player import BasePlayer
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

_TEAM_SUMMARY: List[str] = ["g", "w", "l", "r", "ra", "rpg", "rag", "der"]


class NumericItem(QTableWidgetItem):
    """Table item that sorts numeric values properly."""

    def __init__(self, value: Any, *, align_left: bool = False) -> None:
        super().__init__()
        flags = self.flags() & ~Qt.ItemFlag.ItemIsEditable
        self.setFlags(flags)
        alignment = Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignRight
        self.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        self._set_value(value)

    def _set_value(self, value: Any) -> None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            self.setData(Qt.ItemDataRole.DisplayRole, str(value))
        else:
            display = int(numeric) if numeric.is_integer() else numeric
            self.setData(Qt.ItemDataRole.DisplayRole, display)
            self.setData(Qt.ItemDataRole.EditRole, numeric)


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
            self.resize(1024, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        batter_ids = [
            pid
            for pid in roster.act
            if pid in players and not getattr(players[pid], "is_pitcher", False)
        ]
        pitcher_ids = [
            pid
            for pid in roster.act
            if pid in players and getattr(players[pid], "is_pitcher", False)
        ]

        batters = [players[pid] for pid in batter_ids]
        pitchers = [players[pid] for pid in pitcher_ids]

        self.tabs.addTab(
            self._build_player_tab(batters, _BATTING_COLS, title="Batting"),
            "Batting",
        )
        self.tabs.addTab(
            self._build_player_tab(pitchers, _PITCHING_COLS, title="Pitching"),
            "Pitching",
        )
        self.tabs.addTab(self._build_team_tab(team.season_stats), "Team")

    # ------------------------------------------------------------------
    def _build_player_tab(
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

        is_pitching = columns is _PITCHING_COLS
        for row, player in enumerate(players):
            name = (
                f"{getattr(player, 'first_name', '')} "
                f"{getattr(player, 'last_name', '')}"
            ).strip()
            table.setItem(row, 0, NumericItem(name, align_left=True))
            stats = getattr(player, "season_stats", {}) or {}
            if is_pitching:
                stats = self._normalize_pitching_stats(stats)
            else:
                stats = self._normalize_batting_stats(stats)
            for col, key in enumerate(columns, start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, NumericItem(value))

        table.setSortingEnabled(True)
        card.layout().addWidget(table)
        return card

    def _build_team_tab(self, stats: Dict[str, float] | None) -> Card:
        card = Card()
        card.layout().addWidget(section_title("Team Totals"))

        data = stats or {}
        seen_keys: set[str] = set()
        rows: List[tuple[str, Any]] = []
        for key in _TEAM_SUMMARY:
            if key in data:
                rows.append((key.upper(), data[key]))
                seen_keys.add(key.upper())
        for key, value in sorted(data.items()):
            label = key.upper()
            if label not in seen_keys:
                rows.append((label, value))
                seen_keys.add(label)

        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Stat", "Value"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for idx, (label, value) in enumerate(rows):
            table.setItem(idx, 0, NumericItem(label, align_left=True))
            table.setItem(idx, 1, NumericItem(value))

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
