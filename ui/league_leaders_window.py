from __future__ import annotations

from typing import Iterable, List, Tuple

from types import SimpleNamespace

try:
    from PyQt6.QtCore import Qt
except ImportError:  # pragma: no cover - test stubs
    Qt = SimpleNamespace(
        AlignmentFlag=SimpleNamespace(
            AlignCenter=None,
            AlignLeft=None,
            AlignRight=None,
            AlignVCenter=None,
        ),
        ItemDataRole=SimpleNamespace(DisplayRole=None, EditRole=None, UserRole=None),
        ItemFlag=SimpleNamespace(ItemIsEditable=None),
        SortOrder=SimpleNamespace(AscendingOrder=None, DescendingOrder=None),
    )
try:
    from PyQt6.QtWidgets import (
        QDialog,
        QGridLayout,
        QHeaderView,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - test stubs
    class _QtDummy:
        EditTrigger = SimpleNamespace(NoEditTriggers=None)
        SelectionBehavior = SimpleNamespace(SelectRows=None)

        def __init__(self, *args, **kwargs) -> None:
            pass

        def __getattr__(self, name):
            def _dummy(*_args, **_kwargs):
                return self

            return _dummy

    QDialog = QGridLayout = QTableWidget = QTableWidgetItem = QVBoxLayout = _QtDummy

    class QHeaderView:  # type: ignore[too-many-ancestors]
        class ResizeMode:
            Stretch = None
            ResizeToContents = None

from models.base_player import BasePlayer
from .components import Card, section_title
from .stat_helpers import format_number, top_players

_BATTING_CATEGORIES: List[Tuple[str, str, bool, bool, int]] = [
    ("Average", "avg", False, False, 3),
    ("Home Runs", "hr", True, False, 0),
    ("RBI", "rbi", True, False, 0),
    ("Stolen Bases", "sb", True, False, 0),
    ("On-Base %", "obp", False, False, 3),
]

_PITCHING_CATEGORIES: List[Tuple[str, str, bool, bool, int]] = [
    ("ERA", "era", False, True, 2),
    ("WHIP", "whip", False, True, 2),
    ("Wins", "w", True, True, 0),
    ("Strikeouts", "so", True, True, 0),
    ("Saves", "sv", True, True, 0),
]


class LeagueLeadersWindow(QDialog):
    def __init__(
        self,
        players: Iterable[BasePlayer],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("League Leaders")
        if callable(getattr(self, "resize", None)):
            self.resize(960, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        player_list = list(players)
        hitters = [p for p in player_list if not getattr(p, "is_pitcher", False)]
        pitchers = [p for p in player_list if getattr(p, "is_pitcher", False)]

        layout.addWidget(self._build_leader_section("Batting Leaders", hitters, _BATTING_CATEGORIES))
        layout.addWidget(self._build_leader_section("Pitching Leaders", pitchers, _PITCHING_CATEGORIES))

    def _build_leader_section(
        self,
        title: str,
        players: List[BasePlayer],
        categories: List[Tuple[str, str, bool, bool, int]],
    ) -> Card:
        card = Card()
        card.layout().addWidget(section_title(title))
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)
        for idx, (label, key, descending, pitcher_only, decimals) in enumerate(categories):
            leaders = top_players(players, key, pitcher_only=pitcher_only, descending=descending, limit=5)
            table = QTableWidget(len(leaders), 3)
            table.setHorizontalHeaderLabels([label, "Player", "Value"])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            for row, (player, value) in enumerate(leaders):
                table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                name = f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip()
                item = QTableWidgetItem(name)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 1, item)
                table.setItem(row, 2, QTableWidgetItem(format_number(value, decimals=decimals)))
            grid.addWidget(table, idx // 2, idx % 2)
        card.layout().addLayout(grid)
        return card


