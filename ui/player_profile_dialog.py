"""Dialog for displaying a player's profile with avatar, info,
ratings and stats."""

import os
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
    QGroupBox,
)

from models.base_player import BasePlayer
from utils.stats_persistence import load_stats


class PlayerProfileDialog(QDialog):
    """Display basic information, current ratings and stats for a player."""

    def __init__(self, player: BasePlayer, parent=None):
        super().__init__(parent)
        self.player = player
        self.setWindowTitle(f"{player.first_name} {player.last_name}")

        layout = QVBoxLayout()
        layout.addLayout(self._build_header())

        ratings = self._collect_ratings()
        if ratings:
            layout.addWidget(self._build_horizontal_grid("Ratings", ratings))

        stats_history = self._collect_stats_history()
        layout.addWidget(self._build_stats_table(stats_history))

        self.setLayout(layout)
        self._apply_espn_style()
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    # ------------------------------------------------------------------
    def _build_header(self) -> QHBoxLayout:
        """Create the top section with avatar and basic info."""
        layout = QHBoxLayout()

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
        layout.addWidget(avatar_label)

        info_layout = QVBoxLayout()
        info_layout.addWidget(
            QLabel(f"Name: {self.player.first_name} {self.player.last_name}")
        )
        age = self._calculate_age(self.player.birthdate)
        info_layout.addWidget(QLabel(f"Age: {age}"))
        info_layout.addWidget(
            QLabel(f"Height: {getattr(self.player, 'height', '?')}")
        )
        info_layout.addWidget(
            QLabel(f"Weight: {getattr(self.player, 'weight', '?')}")
        )
        info_layout.addWidget(
            QLabel(f"Bats: {getattr(self.player, 'bats', '?')}")
        )
        positions = ", ".join(
            p
            for p in [
                self.player.primary_position,
                *getattr(self.player, "other_positions", []),
            ]
            if p
        )
        info_layout.addWidget(QLabel(f"Positions: {positions}"))
        layout.addLayout(info_layout)

        return layout

    def _collect_ratings(self) -> Dict[str, Any]:
        """Gather non-potential numeric ratings for the player."""
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
        }
        ratings = {}
        for key, val in vars(self.player).items():
            if key in excluded or key.startswith("pot_"):
                continue
            if isinstance(val, (int, float)):
                ratings[key] = val
        return ratings

    def _collect_stats_history(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Gather season, career and historical stats for the player."""

        history: List[Tuple[str, Dict[str, Any]]] = []
        for year, _r_hist, s_hist in self._load_history():
            if s_hist:
                history.append((year, s_hist))

        season = self._stats_to_dict(getattr(self.player, "season_stats", {}))
        if season:
            history.append(("Current", season))

        career = self._stats_to_dict(getattr(self.player, "career_stats", {}))
        if career:
            history.append(("Career", career))

        return history

    def _stats_to_dict(self, stats: Any) -> Dict[str, Any]:
        if isinstance(stats, dict):
            return stats
        if is_dataclass(stats):
            return asdict(stats)
        return {}

    def _load_history(self) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
        """Return lists of rating and stat histories keyed by year."""

        data = load_stats()
        history: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
        rating_fields = getattr(type(self.player), "_rating_fields", set())
        for idx, entry in enumerate(data.get("history", []), start=1):
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
            history.append((f"Year {idx}", ratings, stats))
        return history

    def _build_horizontal_grid(self, title: str, data: Dict[str, Any]) -> QGroupBox:
        """Create a two-row grid with headers across the top."""

        group = QGroupBox(title)
        grid = QGridLayout()
        for col, (key, val) in enumerate(data.items()):
            grid.addWidget(
                QLabel(str(key).replace("_", " ").title()),
                0,
                col,
            )
            grid.addWidget(QLabel(str(val)), 1, col)
        group.setLayout(grid)
        return group

    def _build_stats_table(self, rows: List[Tuple[str, Dict[str, Any]]]) -> QGroupBox:
        """Create a grid showing stats by year with columns for each stat."""

        group = QGroupBox("Stats")
        grid = QGridLayout()
        if not rows:
            grid.addWidget(QLabel("No stats available"), 0, 0)
            group.setLayout(grid)
            return group

        columns = sorted({k for _year, data in rows for k in data.keys()})
        grid.addWidget(QLabel("Year"), 0, 0)
        for col, key in enumerate(columns, start=1):
            grid.addWidget(
                QLabel(str(key).replace("_", " ").title()),
                0,
                col,
            )

        for row_idx, (year, data) in enumerate(rows, start=1):
            grid.addWidget(QLabel(year), row_idx, 0)
            for col_idx, key in enumerate(columns, start=1):
                grid.addWidget(QLabel(str(data.get(key, ""))), row_idx, col_idx)

        group.setLayout(grid)
        return group

    def _apply_espn_style(self) -> None:
        """Apply ESPN-like color scheme."""
        qss_path = os.path.join(
            os.path.dirname(__file__), "resources", "espn.qss"
        )
        if os.path.exists(qss_path) and callable(getattr(self, "setStyleSheet", None)):
            with open(qss_path, "r", encoding="utf-8") as qss_file:
                self.setStyleSheet(qss_file.read())

    def _calculate_age(self, birthdate_str: str):
        try:
            birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            return today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )
        except Exception:
            return "?"
