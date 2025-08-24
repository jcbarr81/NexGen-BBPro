"""Dialog for displaying a player's profile with avatar, info,
ratings and stats."""

import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict

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
            layout.addWidget(self._build_grid("Ratings", ratings))

        for attr, label in [
            ("season_stats", "Season Stats"),
            ("career_stats", "Career Stats"),
        ]:
            if hasattr(player, attr):
                stats = self._stats_to_dict(getattr(player, attr))
                if stats:
                    layout.addWidget(self._build_grid(label, stats))

        self.setLayout(layout)
        self._apply_espn_style()

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
            [
                self.player.primary_position,
                *getattr(self.player, "other_positions", []),
            ]
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

    def _stats_to_dict(self, stats: Any) -> Dict[str, Any]:
        if isinstance(stats, dict):
            return stats
        if is_dataclass(stats):
            return asdict(stats)
        return {}

    def _build_grid(self, title: str, data: Dict[str, Any]) -> QGroupBox:
        group = QGroupBox(title)
        grid = QGridLayout()
        for row, (key, val) in enumerate(data.items()):
            grid.addWidget(
                QLabel(str(key).replace("_", " ").title()),
                row,
                0,
            )
            grid.addWidget(QLabel(str(val)), row, 1)
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
