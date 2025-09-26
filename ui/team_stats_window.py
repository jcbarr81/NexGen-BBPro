from __future__ import annotations

from typing import Any, Dict, Iterable, List

import csv
import json
from pathlib import Path
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

    QComboBox = QDialog = QHBoxLayout = QLabel = QLineEdit = QPushButton = QTabWidget = QTableWidget = QTableWidgetItem = QVBoxLayout = _QtDummy

    class QHeaderView:  # type: ignore[too-many-ancestors]
        class ResizeMode:
            Stretch = None
            ResizeToContents = None

from models.team import Team
from models.roster import Roster
from models.base_player import BasePlayer
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PLAYERS_FILE = DATA_DIR / "players.csv"
STATS_FILE = DATA_DIR / "season_stats.json"


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



def _games_from_history() -> dict[str, int]:
    try:
        data = json.loads(STATS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}
    history = data.get('history', [])
    last_pa: dict[str, int] = {}
    games: dict[str, int] = {}
    for snap in history:
        players = snap.get('players', {}) or {}
        for pid, stats in players.items():
            try:
                pa = int(stats.get('pa', 0) or 0)
            except Exception:
                pa = 0
            prev = last_pa.get(pid)
            if prev is None:
                if pa > 0:
                    games[pid] = games.get(pid, 0) + 1
            else:
                if pa > prev:
                    games[pid] = games.get(pid, 0) + 1
            last_pa[pid] = pa
    return games
def _load_players_lookup() -> tuple[Dict[str, SimpleNamespace], Dict[str, Dict[str, Any]]]:
    try:
        with STATS_FILE.open('r', encoding='utf-8') as handle:
            stats = json.load(handle)
    except (OSError, json.JSONDecodeError):
        stats = {"players": {}, "teams": {}}
    player_stats: Dict[str, Dict[str, Any]] = stats.get('players', {})
    team_stats: Dict[str, Dict[str, Any]] = stats.get('teams', {})
    lookup: Dict[str, SimpleNamespace] = {}
    try:
        with PLAYERS_FILE.open('r', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                pid = row['player_id']
                stats_block = _normalize_player_stats(player_stats.get(pid))
                is_pitcher = str(row.get('is_pitcher', '')).strip().lower() in {'1', 'true', 'yes'}
                lookup[pid] = SimpleNamespace(
                    player_id=pid,
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    is_pitcher=is_pitcher,
                    season_stats=stats_block,
                )
    except OSError:
        lookup = {}
    return lookup, team_stats


from .components import Card, section_title, build_metric_row
from .stat_helpers import (
    format_number,
    format_ip,
    batting_summary,
    pitching_summary,
)

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

_TEAM_COLUMNS: List[str] = ["g", "w", "l", "r", "ra", "opp_pa", "opp_hr"]


class TeamStatsWindow(QDialog):
    def __init__(
        self,
        team: Team,
        players: Dict[str, BasePlayer],
        roster: Roster,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.team = team
        player_lookup, team_stats = _load_players_lookup()
        self.players = player_lookup
        try:
            self.roster = load_roster(team.team_id)
        except Exception:
            self.roster = roster

        hist_games = _games_from_history()
        for pid, entry in self.players.items():
            g = int(entry.season_stats.get('g', 0) or 0)
            entry.season_stats['g'] = max(g, int(hist_games.get(pid, 0)))
        team.season_stats = _normalize_team_stats(team_stats.get(team.team_id))

        self.setWindowTitle("Team Statistics")
        if callable(getattr(self, "resize", None)):
            self.resize(1100, 680)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        layout.addWidget(self._build_header(team))

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        batter_ids = [
            pid
            for pid in roster.act
            if pid in self.players and not getattr(self.players[pid], "is_pitcher", False)
        ]
        pitcher_ids = [
            pid
            for pid in roster.act
            if pid in self.players and getattr(self.players[pid], "is_pitcher", False)
        ]

        batters = [self.players[pid] for pid in batter_ids]
        pitchers = [self.players[pid] for pid in pitcher_ids]

        self.tabs.addTab(
            self._build_player_tab(batters, _BATTING_COLS, title="Batting"),
            "Batting",
        )
        self.tabs.addTab(
            self._build_player_tab(pitchers, _PITCHING_COLS, title="Pitching"),
            "Pitching",
        )
        self.tabs.addTab(self._build_team_totals(team), "Team Totals")

    def _build_header(self, team: Team) -> Card:
        card = Card()
        name = f"{team.city} {team.name}".strip()
        card.layout().addWidget(section_title(name))

        stats = dict(getattr(team, "season_stats", {}) or {})
        wins = int(stats.get("w", 0))
        losses = int(stats.get("l", 0))
        games = stats.get("g", 0)
        run_diff = stats.get("r", 0) - stats.get("ra", 0)
        pct = wins / (wins + losses) if (wins + losses) else 0.0
        metrics = [
            ("Record", f"{wins}-{losses}"),
            ("Win %", format_number(pct, decimals=3)),
            ("Games", format_number(games, decimals=0)),
            ("Run Diff", format_number(run_diff, decimals=0)),
            ("Runs", format_number(stats.get("r", 0), decimals=0)),
            ("Runs Allowed", format_number(stats.get("ra", 0), decimals=0)),
        ]
        card.layout().addWidget(build_metric_row(metrics, columns=3))
        return card

    def _build_player_tab(
        self,
        players: Iterable[BasePlayer],
        columns: List[str],
        *,
        title: str,
    ) -> Card:
        player_list = list(players)
        card = Card()
        card.layout().addWidget(section_title(title))

        summary = batting_summary(player_list) if columns is _BATTING_COLS else pitching_summary(player_list)
        if summary:
            card.layout().addWidget(build_metric_row(summary, columns=min(len(summary), 5)))

        headers = ["Name"] + [col.upper() for col in columns]
        table = QTableWidget(len(player_list), len(headers))
        self._configure_table(table, headers)

        is_pitching = columns is _PITCHING_COLS
        for row, player in enumerate(player_list):
            name = f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip()
            table.setItem(row, 0, self._text_item(name, align_left=True))
            stats = getattr(player, 'season_stats', {}) or {}
            stats = self._normalize_pitching(stats) if is_pitching else self._normalize_batting(stats)
            for col, key in enumerate(columns, start=1):
                value = stats.get(key, 0)
                table.setItem(row, col, self._stat_item(key, value))

        sort_index = 1 if table.columnCount() > 1 else 0
        placeholder = f"Search {'pitchers' if is_pitching else 'hitters'}"
        self._attach_table_controls(card, table, placeholder=placeholder, default_sort=sort_index)
        card.layout().addWidget(table)
        return card

    def _build_team_totals(self, team: Team) -> Card:
        card = Card()
        card.layout().addWidget(section_title("Team Totals"))

        stats = dict(getattr(team, "season_stats", {}) or {})
        headers = ["Category", "Value"]
        rows = [(key.upper(), stats.get(key, 0)) for key in _TEAM_COLUMNS]

        table = QTableWidget(len(rows), len(headers))
        self._configure_table(table, headers)

        for row, (label, value) in enumerate(rows):
            table.setItem(row, 0, self._text_item(label, align_left=True))
            table.setItem(row, 1, self._stat_item(label, value))

        self._attach_table_controls(card, table, placeholder="Search categories", default_sort=0)
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




