from __future__ import annotations

from typing import Any, Dict, Iterable, List

import csv
import json
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from models.team import Team
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PLAYERS_FILE = DATA_DIR / "players.csv"
STATS_FILE = DATA_DIR / "season_stats.json"


def _games_from_history() -> Dict[str, int]:
    """Return max games played per player from history snapshots."""
    try:
        with STATS_FILE.open('r', encoding='utf-8') as handle:
            stats = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    history = stats.get('history', [])
    games: Dict[str, int] = {}
    for snapshot in history:
        players = snapshot.get('players', {}) if isinstance(snapshot, dict) else {}
        if not isinstance(players, dict):
            continue
        for player_id, data in players.items():
            if not isinstance(data, dict):
                continue
            value = data.get('g', data.get('games'))
            if value is None:
                continue
            try:
                games_played = int(float(value))
            except (TypeError, ValueError):
                continue
            if games_played > games.get(player_id, 0):
                games[player_id] = games_played
    return games


def _normalize_player_stats(data: Dict[str, Any] | None) -> Dict[str, Any]:
    stats = dict(data or {})
    if 'b2' in stats and '2b' not in stats:
        stats['2b'] = stats.get('b2', 0)
    if 'b3' in stats and '3b' not in stats:
        stats['3b'] = stats.get('b3', 0)
    stats.setdefault('w', stats.get('wins', stats.get('w', 0)))
    stats.setdefault('l', stats.get('losses', stats.get('l', 0)))
    return stats


def _normalize_team_stats(data: Dict[str, Any] | None) -> Dict[str, Any]:
    stats = dict(data or {})
    stats.setdefault('w', stats.get('wins', stats.get('w', 0)))
    stats.setdefault('l', stats.get('losses', stats.get('l', 0)))
    stats.setdefault('g', stats.get('g', stats.get('games', 0)))
    stats.setdefault('r', stats.get('r', 0))
    stats.setdefault('ra', stats.get('ra', 0))
    return stats


def _load_players_with_stats() -> tuple[list[SimpleNamespace], Dict[str, Any]]:
    try:
        with STATS_FILE.open('r', encoding='utf-8') as handle:
            stats = json.load(handle)
    except (OSError, json.JSONDecodeError):
        stats = {"players": {}, "teams": {}}
    player_stats: Dict[str, Dict[str, Any]] = stats.get('players', {})
    team_stats: Dict[str, Dict[str, Any]] = stats.get('teams', {})
    entries: list[SimpleNamespace] = []
    meta: Dict[str, Dict[str, str]] = {}
    try:
        with PLAYERS_FILE.open('r', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            meta = {row['player_id']: row for row in reader}
    except OSError:
        meta = {}
    for pid, data in meta.items():
        stats_block = _normalize_player_stats(player_stats.get(pid))
        is_pitcher = str(data.get('is_pitcher', '')).strip().lower() in {'1', 'true', 'yes'}
        entry = SimpleNamespace(
            player_id=pid,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            is_pitcher=is_pitcher,
            season_stats=stats_block,
        )
        entries.append(entry)
    return entries, team_stats


from models.base_player import BasePlayer
from .components import Card, section_title, build_metric_row
from .stat_helpers import (
    format_number,
    format_ip,
    batting_summary,
    pitching_summary,
)

_TEAM_COLUMNS: List[str] = ["team", "g", "w", "l", "r", "ra", "der"]
_BATTING_COLS: List[str] = ["g", "ab", "r", "h", "2b", "3b", "hr", "rbi", "bb", "so", "sb", "avg", "obp", "slg"]
_PITCHING_COLS: List[str] = ["w", "l", "era", "g", "gs", "sv", "ip", "h", "er", "bb", "so", "whip"]


class LeagueStatsWindow(QDialog):
    def __init__(
        self,
        teams: Iterable[Team],
        players: Iterable[BasePlayer],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("League Statistics")
        if callable(getattr(self, "resize", None)):
            self.resize(1120, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        teams = list(teams)
        player_entries, team_stats = _load_players_with_stats()

        hist_games = _games_from_history()
        for e in player_entries:
            g = int(e.season_stats.get('g', 0) or 0)
            g = max(g, int(hist_games.get(e.player_id, 0)))
            e.season_stats['g'] = g


        for team in teams:
            team.season_stats = _normalize_team_stats(team_stats.get(team.team_id))

        batters = [p for p in player_entries if not getattr(p, "is_pitcher", False)]
        pitchers = [p for p in player_entries if getattr(p, "is_pitcher", False)]

        layout.addWidget(self._build_header(teams, batters, pitchers))

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.tabs.addTab(self._build_team_tab(teams), "Teams")
        self.tabs.addTab(self._build_player_tab(batters, _BATTING_COLS, title="League Batting"), "Batters")
        self.tabs.addTab(self._build_player_tab(pitchers, _PITCHING_COLS, title="League Pitching"), "Pitchers")

    def _build_header(
        self,
        teams: List[Team],
        batters: List[BasePlayer],
        pitchers: List[BasePlayer],
    ) -> Card:
        card = Card()
        card.layout().addWidget(section_title("League Snapshot"))

        batting_metrics = batting_summary(batters)
        pitching_metrics = pitching_summary(pitchers)
        metrics = [
            ("Teams", format_number(len(teams), decimals=0)),
            batting_metrics[0],  # AVG
            batting_metrics[1],  # OBP
            ("HR", batting_metrics[4][1]),
            pitching_metrics[0],  # ERA
            pitching_metrics[1],  # WHIP
            ("K/9", pitching_metrics[2][1]),
        ]
        card.layout().addWidget(build_metric_row(metrics, columns=4))
        return card

    def _build_team_tab(self, teams: List[Team]) -> Card:
        card = Card()
        card.layout().addWidget(section_title("Team Totals"))

        table = QTableWidget(len(teams), len(_TEAM_COLUMNS))
        self._configure_table(table, [col.upper() for col in _TEAM_COLUMNS])

        for row, team in enumerate(teams):
            stats = team.season_stats or {}
            table.setItem(row, 0, self._text_item(f"{team.city} {team.name}", align_left=True))
            for col, key in enumerate(_TEAM_COLUMNS[1:], start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, self._stat_item(key, value))

        self._attach_table_controls(card, table, placeholder="Search teams or metrics", default_sort=1)
        card.layout().addWidget(table)
        return card

    def _build_player_tab(
        self,
        players: List[BasePlayer],
        columns: List[str],
        *,
        title: str,
    ) -> Card:
        card = Card()
        card.layout().addWidget(section_title(title))

        headers = ["Player"] + [col.upper() for col in columns]
        table = QTableWidget(len(players), len(headers))
        self._configure_table(table, headers)

        is_pitching = columns is _PITCHING_COLS
        for row, player in enumerate(players):
            name = f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip()
            table.setItem(row, 0, self._text_item(name, align_left=True))
            stats = getattr(player, 'season_stats', {}) or {}
            stats = self._normalize_pitching(stats) if is_pitching else self._normalize_batting(stats)
            for col, key in enumerate(columns, start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, self._stat_item(key, value))

        sort_index = 1 if table.columnCount() > 1 else 0
        placeholder = "Search players or stats"
        self._attach_table_controls(card, table, placeholder=placeholder, default_sort=sort_index)
        card.layout().addWidget(table)
        return card

    def _configure_table(self, table: QTableWidget, headers: List[str]) -> None:
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        if headers:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.setWordWrap(False)
        table.setSortingEnabled(True)

    def _attach_table_controls(
        self,
        card: Card,
        table: QTableWidget,
        *,
        placeholder: str,
        default_sort: int = 0,
    ) -> None:
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        label = QLabel("Filter:")
        search = QLineEdit()
        search.setPlaceholderText(placeholder)
        clear_btn = QPushButton("Clear")
        sort_label = QLabel("Sort by:")
        sort_combo = QComboBox()
        for col in range(table.columnCount()):
            header = table.horizontalHeaderItem(col)
            header_text = header.text() if header else str(col)
            sort_combo.addItem(header_text, col)
        if default_sort >= table.columnCount():
            default_sort = 0
        sort_combo.setCurrentIndex(default_sort)

        controls.addWidget(label)
        controls.addWidget(search, 1)
        controls.addWidget(clear_btn)
        controls.addSpacing(12)
        controls.addWidget(sort_label)
        controls.addWidget(sort_combo)
        controls.addStretch(1)
        card.layout().addLayout(controls)

        def apply_filter() -> None:
            term = search.text().strip().lower()
            for row in range(table.rowCount()):
                match = not term
                if not match:
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        if item and term in item.text().lower():
                            match = True
                            break
                table.setRowHidden(row, not match)

        def apply_sort() -> None:
            column = sort_combo.currentData()
            if column is None:
                return
            order = Qt.SortOrder.AscendingOrder if int(column) == 0 else Qt.SortOrder.DescendingOrder
            table.sortItems(int(column), order)

        search.textChanged.connect(apply_filter)
        clear_btn.clicked.connect(lambda: search.clear())
        sort_combo.currentIndexChanged.connect(lambda _: apply_sort())

        apply_sort()

    def _text_item(self, text: str, *, align_left: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        alignment = Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignRight
        item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        return item

    def _stat_item(self, key: str, value: Any) -> QTableWidgetItem:
        key_lower = key.lower()
        if key_lower in {"avg", "obp", "slg", "era", "whip"}:
            display = format_number(value, decimals=3)
        elif key_lower == "ip":
            display = format_ip(value)
        else:
            display = format_number(value, decimals=0)
        item = QTableWidgetItem(display)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        try:
            numeric = float(display)
        except ValueError:
            numeric = 0.0
        item.setData(Qt.ItemDataRole.EditRole, numeric)
        return item

    def _normalize_batting(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(stats)
        if "b2" in data and "2b" not in data:
            data["2b"] = data.get("b2", 0)
        if "b3" in data and "3b" not in data:
            data["3b"] = data.get("b3", 0)
        return data

    def _normalize_pitching(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(stats)
        if "ip" not in data:
            outs = data.get("outs")
            if outs is not None:
                data["ip"] = outs / 3
        ip = data.get("ip", 0)
        if ip:
            er = data.get("er", 0)
            walks_hits = data.get("bb", 0) + data.get("h", 0)
            data.setdefault("era", (er * 9) / ip if ip else 0.0)
            data.setdefault("whip", walks_hits / ip if ip else 0.0)
        data.setdefault("w", data.get("wins", data.get("w", 0)))
        data.setdefault("l", data.get("losses", data.get("l", 0)))
        return data


