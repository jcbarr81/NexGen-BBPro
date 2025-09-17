"""Dialog for displaying a player profile with themed styling."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QWidget,
)

from models.base_player import BasePlayer
from utils.stats_persistence import load_stats
from .components import Card, section_title


_BATTING_STATS: List[str] = [
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

_PITCHING_STATS: List[str] = [
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

_PITCHER_RATING_LABELS: Dict[str, str] = {
    "endurance": "EN",
    "control": "CO",
    "movement": "MO",
    "hold_runner": "HR",
}


class PlayerProfileDialog(QDialog):
    """Display player information, ratings and stats using themed cards."""

    def __init__(self, player: BasePlayer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.player = player
        self.setWindowTitle(f"{player.first_name} {player.last_name}")

        root = QVBoxLayout()
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        root.addWidget(self._build_header_card())

        ratings = self._collect_ratings()
        if ratings:
            root.addWidget(self._build_ratings_card(ratings))

        stats_history = self._collect_stats_history()
        root.addWidget(self._build_stats_card(stats_history))

        root.addStretch()
        self.setLayout(root)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    # ------------------------------------------------------------------
    def _build_header_card(self) -> Card:
        card = Card()
        layout = card.layout()
        layout.addWidget(section_title("Player Profile"))

        container = QWidget()
        hbox = QHBoxLayout(container)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(18)

        avatar_label = QLabel()
        pix = QPixmap(f"images/avatars/{self.player.player_id}.png")
        if pix.isNull():
            pix = QPixmap("images/avatars/default.png")
        if not pix.isNull():
            pix = pix.scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        avatar_label.setPixmap(pix)
        avatar_label.setFixedSize(128, 128)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hbox.addWidget(avatar_label, 0)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)
        info_layout.addWidget(QLabel(f"Name: {self.player.first_name} {self.player.last_name}"))
        age = self._calculate_age(self.player.birthdate)
        info_layout.addWidget(QLabel(f"Age: {age}"))
        info_layout.addWidget(QLabel(f"Height: {self._format_height(getattr(self.player, 'height', None))}"))
        info_layout.addWidget(QLabel(f"Weight: {getattr(self.player, 'weight', '?')}"))
        info_layout.addWidget(QLabel(f"Bats: {getattr(self.player, 'bats', '?')}"))
        positions = ", ".join(
            p
            for p in [self.player.primary_position, *getattr(self.player, "other_positions", [])]
            if p
        )
        info_layout.addWidget(QLabel(f"Positions: {positions}"))
        hbox.addWidget(info_widget, 1)

        layout.addWidget(container)
        return card

    def _build_ratings_card(self, ratings: Dict[str, Any]) -> Card:
        card = Card()
        layout = card.layout()
        layout.addWidget(section_title("Ratings"))

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        for col, (label, value) in enumerate(ratings.items()):
            header = QLabel(label)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label = QLabel(self._format_stat(value))
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(header, 0, col)
            grid.addWidget(value_label, 1, col)

        grid_widget = QWidget()
        grid_widget.setLayout(grid)
        layout.addWidget(grid_widget)
        return card

    def _build_stats_card(self, rows: List[Tuple[str, Dict[str, Any]]]) -> Card:
        card = Card()
        layout = card.layout()
        layout.addWidget(section_title("Stats"))

        if not rows:
            layout.addWidget(QLabel("No stats available"))
            return card

        is_pitcher = getattr(self.player, "is_pitcher", False)
        columns = _PITCHING_STATS if is_pitcher else _BATTING_STATS

        table = QTableWidget(len(rows), len(columns) + 1)
        headers = ["Year"] + [c.upper() for c in columns]
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row_idx, (year, data) in enumerate(rows):
            table.setItem(row_idx, 0, self._stat_item(year, align_left=True))
            for col_idx, key in enumerate(columns, start=1):
                value = data.get(key, "")
                table.setItem(row_idx, col_idx, self._stat_item(value))

        table.setSortingEnabled(True)
        layout.addWidget(table)
        return card

    # ------------------------------------------------------------------
    def _collect_ratings(self) -> Dict[str, Any]:
        excluded = {
            "player_id",
            "first_name",
            "last_name",
            "birthdate",
            "height",
            "weight",
            "bats",
            "primary_position",
            "other_positions",
            "gf",
            "injured",
            "injury_description",
            "return_date",
            "ready",
        }
        values: Dict[str, Any] = {}
        for key, val in vars(self.player).items():
            if key in excluded or key.startswith("pot_"):
                continue
            if isinstance(val, (int, float)):
                values[key] = val

        if getattr(self.player, "is_pitcher", False):
            ordered: Dict[str, Any] = {}
            for key in ("endurance", "control", "movement", "hold_runner"):
                if key in values:
                    ordered[_PITCHER_RATING_LABELS.get(key, key.upper())] = values.pop(key)
            for key in sorted(values):
                ordered[key.upper()] = values[key]
            return ordered

        ordered: Dict[str, Any] = {}
        for key in sorted(values):
            ordered[key.replace("_", " ").title()] = values[key]
        return ordered

    def _collect_stats_history(self) -> List[Tuple[str, Dict[str, Any]]]:
        history: List[Tuple[str, Dict[str, Any]]] = []
        is_pitcher = getattr(self.player, "is_pitcher", False)
        for year, _ratings, stats in self._load_history():
            if stats:
                history.append((year, self._stats_to_dict(stats, is_pitcher)))

        season = self._stats_to_dict(getattr(self.player, "season_stats", {}), is_pitcher)
        if season:
            history.append(("Current", season))

        career = self._stats_to_dict(getattr(self.player, "career_stats", {}), is_pitcher)
        if career:
            history.append(("Career", career))

        return history

    def _load_history(self) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
        data = load_stats()
        history: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
        rating_fields = getattr(type(self.player), "_rating_fields", set())
        entries = data.get("history", [])[-5:]
        used_years: set[str] = set()
        for entry in entries:
            player_data = entry.get("players", {}).get(self.player.player_id)
            if not player_data:
                continue
            if "ratings" in player_data or "stats" in player_data:
                ratings = player_data.get("ratings", {})
                stats = player_data.get("stats", {})
            else:
                ratings = {
                    k: v
                    for k, v in player_data.items()
                    if k in rating_fields and not k.startswith("pot_")
                }
                stats = {
                    k: v
                    for k, v in player_data.items()
                    if k not in rating_fields and not k.startswith("pot_")
                }
            year = entry.get("year")
            year_label = str(year) if year is not None else f"Year {len(history) + 1}"
            if year_label in used_years:
                continue
            used_years.add(year_label)
            history.append((year_label, ratings, stats))
        return history

    def _stats_to_dict(self, stats: Any, is_pitcher: bool) -> Dict[str, Any]:
        if isinstance(stats, dict):
            data = dict(stats)
        elif is_dataclass(stats):
            data = asdict(stats)
        else:
            return {}

        if is_pitcher:
            return self._normalize_pitching_stats(data)

        if "b2" in data and "2b" not in data:
            data["2b"] = data.get("b2", 0)
        if "b3" in data and "3b" not in data:
            data["3b"] = data.get("b3", 0)
        return data

    def _normalize_pitching_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        outs = result.get("outs")
        if outs is not None and "ip" not in result:
            result["ip"] = outs / 3
        ip = result.get("ip", 0)
        if ip:
            er = result.get("er", 0)
            result.setdefault("era", (er * 9) / ip if ip else 0.0)
            walks_hits = result.get("bb", 0) + result.get("h", 0)
            result.setdefault("whip", walks_hits / ip if ip else 0.0)
        result.setdefault("w", result.get("wins", result.get("w", 0)))
        result.setdefault("l", result.get("losses", result.get("l", 0)))
        return result

    def _stat_item(self, value: Any, *, align_left: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem()
        alignment = Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignRight
        item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        if isinstance(value, (int, float)):
            item.setData(Qt.ItemDataRole.DisplayRole, self._format_stat(value))
            item.setData(Qt.ItemDataRole.EditRole, float(value))
            return item
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            item.setData(Qt.ItemDataRole.DisplayRole, str(value))
        else:
            item.setData(Qt.ItemDataRole.DisplayRole, self._format_stat(numeric))
            item.setData(Qt.ItemDataRole.EditRole, numeric)
        return item

    def _format_stat(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    def _format_height(self, height: Any) -> str:
        try:
            total_inches = int(height)
        except (TypeError, ValueError):
            return "?"
        feet, inches = divmod(total_inches, 12)
        return f"{feet}'{inches}\""

    def _calculate_age(self, birthdate_str: str):
        try:
            birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            return today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )
        except Exception:
            return "?"
