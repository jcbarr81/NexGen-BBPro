from __future__ import annotations

from typing import Iterable, List, Tuple, Dict, Any, Optional

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
        QTabWidget,
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

    QDialog = QGridLayout = QTableWidget = QTableWidgetItem = QVBoxLayout = QTabWidget = _QtDummy

    class QHeaderView:  # type: ignore[too-many-ancestors]
        class ResizeMode:
            Stretch = None
            ResizeToContents = None

from models.base_player import BasePlayer
from .components import Card, section_title, ensure_layout


def _call_if_exists(obj, method: str, *args, **kwargs) -> None:
    func = getattr(obj, method, None)
    if callable(func):
        try:
            func(*args, **kwargs)
        except Exception:
            pass
from .stat_helpers import format_number, top_players
from utils.player_loader import load_players_from_csv
from utils.path_utils import get_base_dir
from utils.stats_persistence import load_stats as _load_season_stats

DATA_DIR = get_base_dir() / "data"
PLAYERS_FILE = DATA_DIR / "players.csv"

_BATTING_CATEGORIES: List[Tuple[str, str, bool, bool, int]] = [
    # Batting rate stats should sort high→low (descending=True)
    ("Average", "avg", True, False, 3),
    ("Home Runs", "hr", True, False, 0),
    ("RBI", "rbi", True, False, 0),
    ("Stolen Bases", "sb", True, False, 0),
    ("On-Base %", "obp", True, False, 3),
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
        if callable(getattr(self, "setWindowTitle", None)):
            self.setWindowTitle("League Leaders")
        if callable(getattr(self, "resize", None)):
            self.resize(960, 640)

        layout = QVBoxLayout(self)
        if callable(getattr(layout, "setContentsMargins", None)):
            layout.setContentsMargins(24, 24, 24, 24)
        if callable(getattr(layout, "setSpacing", None)):
            layout.setSpacing(18)

        # Always refresh from season_stats.json to ensure accuracy
        player_entries = self._load_players_with_stats()
        hitters = [p for p in player_entries if not getattr(p, "is_pitcher", False)]
        pitchers = [p for p in player_entries if getattr(p, "is_pitcher", False)]

        # Determine qualification thresholds from team games
        try:
            stats = _load_season_stats()
            team_stats: Dict[str, Dict[str, Any]] = stats.get("teams", {})
            games_list = [int(v.get("g", 0) or 0) for v in team_stats.values()]
            max_g = max(games_list) if games_list else 0
        except Exception:
            max_g = 0
        # MLB guidelines: 3.1 PA per game and 1.0 IP per game; we approximate
        # PA with AB here per request, using 2.7 AB per game as a rough proxy.
        self._min_ab = max(1, int(round(max_g * 2.7)))
        self._min_ip = max(1, int(round(max_g * 1.0)))

        tabs = QTabWidget()
        layout.addWidget(tabs)
        tabs.addTab(
            self._build_leader_tab(
                "Batting Leaders",
                self._qualified_batters(hitters),
                _BATTING_CATEGORIES,
                fallback_players=hitters,
            ),
            "Batting",
        )
        tabs.addTab(
            self._build_leader_tab(
                "Pitching Leaders",
                self._qualified_pitchers(pitchers),
                _PITCHING_CATEGORIES,
                fallback_players=pitchers,
            ),
            "Pitching",
        )

    def _build_leader_tab(
        self,
        title: str,
        players: List[BasePlayer],
        categories: List[Tuple[str, str, bool, bool, int]],
        *,
        fallback_players: Optional[Iterable[BasePlayer]] = None,
        limit: int = 5,
    ) -> Card:
        card = Card()
        layout = ensure_layout(card)
        _call_if_exists(layout, "addWidget", section_title(title))
        grid = QGridLayout()
        if callable(getattr(grid, "setContentsMargins", None)):
            grid.setContentsMargins(0, 0, 0, 0)
        if callable(getattr(grid, "setSpacing", None)):
            grid.setSpacing(16)
        base_pool = list(players)
        fallback_pool = list(fallback_players) if fallback_players is not None else list(base_pool)
        for idx, (label, key, descending, pitcher_only, decimals) in enumerate(categories):
            category_players = base_pool
            if key == "sv" and pitcher_only:
                # Saves should not be limited by the innings qualifier; consider every pitcher.
                category_players = fallback_pool
            leaders = self._leaders_for_category(
                category_players,
                fallback_pool,
                key,
                pitcher_only=pitcher_only,
                descending=descending,
                limit=limit,
            )
            table = QTableWidget(len(leaders), 3)
            try:
                table.setHorizontalHeaderLabels([label, "Player", "Value"])
                table.verticalHeader().setVisible(False)
                table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
                table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
                header = table.horizontalHeader()
                header.setStretchLastSection(True)
                header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            except Exception:
                pass
            for row, (player, value) in enumerate(leaders):
                try:
                    table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                except Exception:
                    pass
                name = f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip()
                item = QTableWidgetItem(name)
                try:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                except Exception:
                    pass
                try:
                    item.setData(Qt.ItemDataRole.UserRole, getattr(player, 'player_id', ''))
                except Exception:
                    pass
                try:
                    table.setItem(row, 1, item)
                    table.setItem(row, 2, QTableWidgetItem(format_number(value, decimals=decimals)))
                except Exception:
                    pass
            try:
                table.itemDoubleClicked.connect(lambda item, table=table: self._open_player_from_table(item, table))
            except Exception:
                pass
            _call_if_exists(grid, "addWidget", table, idx // 2, idx % 2)
        _call_if_exists(layout, "addLayout", grid)
        return card

    def _leaders_for_category(
        self,
        players: Iterable[BasePlayer],
        fallback_players: Iterable[BasePlayer],
        key: str,
        *,
        pitcher_only: bool,
        descending: bool,
        limit: int,
    ) -> List[Tuple[BasePlayer, Any]]:
        leaders = [
            (player, value)
            for player, value in top_players(
                players,
                key,
                pitcher_only=pitcher_only,
                descending=descending,
                limit=limit,
            )
            if self._has_stat_sample(player, key)
        ]
        if len(leaders) >= limit:
            return leaders
        fallback_list = list(fallback_players)
        if not fallback_list:
            return leaders
        existing = {
            getattr(player, "player_id", None) or id(player) for player, _ in leaders
        }
        for candidate, value in top_players(
            fallback_list,
            key,
            pitcher_only=pitcher_only,
            descending=descending,
            limit=limit * 2,
        ):
            if not self._has_stat_sample(candidate, key):
                continue
            identifier = getattr(candidate, "player_id", None) or id(candidate)
            if identifier in existing:
                continue
            leaders.append((candidate, value))
            existing.add(identifier)
            if len(leaders) >= limit:
                break
        leaders.sort(key=lambda item: self._stat_sort_key(item[1]), reverse=descending)
        return leaders[:limit]

    @staticmethod
    def _stat_sort_key(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _has_stat_sample(self, player: BasePlayer, key: str) -> bool:
        stats = getattr(player, "season_stats", {}) or {}
        if key in {"era", "whip"}:
            ip = stats.get("ip")
            if ip is None:
                outs = stats.get("outs")
                try:
                    ip = (outs or 0) / 3.0
                except Exception:
                    ip = 0.0
            try:
                return float(ip or 0) > 0.0
            except Exception:
                return False
        if key == "avg":
            try:
                return int(stats.get("ab", 0) or 0) > 0
            except Exception:
                return False
        if key == "obp":
            try:
                ab = float(stats.get("ab", 0) or 0)
                bb = float(stats.get("bb", 0) or 0)
                hbp = float(stats.get("hbp", 0) or 0)
                sf = float(stats.get("sf", 0) or 0)
            except Exception:
                return False
            return (ab + bb + hbp + sf) > 0
        return True

    # Load players merged with season stats so leaders reflect current file
    def _load_players_with_stats(self) -> List[BasePlayer]:
        try:
            stats = _load_season_stats()
        except Exception:
            stats = {"players": {}}
        players = {p.player_id: p for p in load_players_from_csv(str(PLAYERS_FILE))}
        for pid, season in stats.get("players", {}).items():
            if pid in players:
                players[pid].season_stats = season
        return list(players.values())

    # ------------------------------------------------------------------
    # Qualification helpers
    def _qualified_batters(self, players: List[BasePlayer]) -> List[BasePlayer]:
        min_ab = getattr(self, "_min_ab", 0)
        qualified: List[BasePlayer] = []
        for p in players:
            stats = getattr(p, "season_stats", {}) or {}
            try:
                ab = int(stats.get("ab", 0) or 0)
            except Exception:
                ab = 0
            if ab >= min_ab:
                qualified.append(p)
        # Fall back to all hitters if no one qualifies
        return qualified or players

    def _qualified_pitchers(self, players: List[BasePlayer]) -> List[BasePlayer]:
        min_ip = getattr(self, "_min_ip", 0)
        qualified: List[BasePlayer] = []
        for p in players:
            stats = getattr(p, "season_stats", {}) or {}
            ip = stats.get("ip")
            if ip is None:
                outs = stats.get("outs")
                try:
                    ip = (outs or 0) / 3.0
                except Exception:
                    ip = 0.0
            try:
                ip_val = float(ip or 0)
            except Exception:
                ip_val = 0.0
            if ip_val >= min_ip:
                qualified.append(p)
        # Fall back to all pitchers if no one qualifies
        return qualified or players

    def _open_player_from_table(self, item: QTableWidgetItem, table: QTableWidget) -> None:
        try:
            row = item.row()
            pid = table.item(row, 1).data(Qt.ItemDataRole.UserRole) if table.item(row,1) else None
            if not pid:
                return
            from pathlib import Path
            from utils.path_utils import get_base_dir
            players = {p.player_id: p for p in load_players_from_csv(str(get_base_dir() / 'data' / 'players.csv'))}
            player = players.get(pid)
            if not player:
                return
            from .player_profile_dialog import PlayerProfileDialog
            dlg = PlayerProfileDialog(player, self)
            if callable(getattr(dlg, 'exec', None)):
                dlg.exec()
        except Exception:
            pass


