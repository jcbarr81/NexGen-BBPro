"""Dialog for displaying a player profile with themed styling."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

try:
    from PyQt6.QtCore import Qt
except ImportError:  # pragma: no cover - test stubs
    Qt = SimpleNamespace(
        AspectRatioMode=SimpleNamespace(KeepAspectRatio=None),
        TransformationMode=SimpleNamespace(SmoothTransformation=None),
        AlignmentFlag=SimpleNamespace(
            AlignCenter=None,
            AlignHCenter=None,
            AlignVCenter=None,
            AlignLeft=None,
            AlignRight=None,
            AlignTop=None,
        ),
        ItemDataRole=SimpleNamespace(
            DisplayRole=None,
            EditRole=None,
            UserRole=None,
        ),
    )

try:
    from PyQt6.QtGui import QPixmap
except ImportError:  # pragma: no cover - test stubs
    class QPixmap:  # type: ignore[too-many-ancestors]
        def __init__(self, *args, **kwargs) -> None:
            self._is_null = True

        def isNull(self) -> bool:
            return self._is_null

        def scaled(self, *args, **kwargs) -> 'QPixmap':
            return self

        def scaledToWidth(self, *args, **kwargs) -> 'QPixmap':
            return self

        def fill(self, *args, **kwargs) -> None:
            self._is_null = False

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QLabel,
        QVBoxLayout,
        QHBoxLayout,
        QFrame,
        QGridLayout,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QWidget,
    )
except ImportError:  # pragma: no cover - test stubs
    class _QtDummy:
        Shape = SimpleNamespace(StyledPanel=None)
        EditTrigger = SimpleNamespace(NoEditTriggers=None)
        SelectionBehavior = SimpleNamespace(SelectRows=None)

        def __init__(self, *args, **kwargs) -> None:
            pass

        def __getattr__(self, name):  # noqa: D401 - simple dummy forwarder
            def _dummy(*_args, **_kwargs):
                return self

            return _dummy

        def addWidget(self, *args, **kwargs) -> None:
            pass

        def addLayout(self, *args, **kwargs) -> None:
            pass

        def addTab(self, *args, **kwargs) -> None:
            pass

        def addStretch(self, *args, **kwargs) -> None:
            pass

        def layout(self):
            return self

        def setLayout(self, *args, **kwargs) -> None:
            pass

        def setContentsMargins(self, *args, **kwargs) -> None:
            pass

        def setSpacing(self, *args, **kwargs) -> None:
            pass

        def setObjectName(self, *args, **kwargs) -> None:
            pass

        def setFrameShape(self, *args, **kwargs) -> None:
            pass

        def setAlignment(self, *args, **kwargs) -> None:
            pass

        def setFixedSize(self, *args, **kwargs) -> None:
            pass

        def setWordWrap(self, *args, **kwargs) -> None:
            pass

        def setText(self, *args, **kwargs) -> None:
            pass

        def setPixmap(self, *args, **kwargs) -> None:
            pass

        def setMinimumSize(self, *args, **kwargs) -> None:
            pass

        def setMinimumWidth(self, *args, **kwargs) -> None:
            pass

        def setMargin(self, *args, **kwargs) -> None:
            pass

        def setProperty(self, *args, **kwargs) -> None:
            pass

        def setData(self, *args, **kwargs) -> None:
            pass

        def setTextAlignment(self, *args, **kwargs) -> None:
            pass

        def setEditTriggers(self, *args, **kwargs) -> None:
            pass

        def setSelectionBehavior(self, *args, **kwargs) -> None:
            pass

        def setAlternatingRowColors(self, *args, **kwargs) -> None:
            pass

        def setHorizontalHeaderLabels(self, *args, **kwargs) -> None:
            pass

        def setSortingEnabled(self, *args, **kwargs) -> None:
            pass

        def setItem(self, *args, **kwargs) -> None:
            pass

        def horizontalHeader(self):
            return self

        def verticalHeader(self):
            return self

        def setSectionResizeMode(self, *args, **kwargs) -> None:
            pass

    QDialog = QLabel = QVBoxLayout = QHBoxLayout = QFrame = QGridLayout = QTabWidget = QTableWidget = QWidget = _QtDummy

    class QTableWidgetItem(_QtDummy):
        pass

    class QHeaderView:  # type: ignore[too-many-ancestors]
        class ResizeMode:
            Stretch = None

from models.base_player import BasePlayer
from utils.stats_persistence import load_stats
from utils.path_utils import get_base_dir
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

    _FIELD_DIAGRAM_CACHE: QPixmap | None = None

    def __init__(self, player: BasePlayer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.player = player
        self.setWindowTitle(f"{player.first_name} {player.last_name}")

        self._is_pitcher = getattr(player, "is_pitcher", False)

        root = QVBoxLayout()
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        header = self._build_header_section()
        root.addWidget(header)

        overview = self._build_overview_section()
        if overview is not None:
            root.addWidget(overview)

        stats_history = self._collect_stats_history()
        root.addWidget(self._build_stats_section(stats_history))

        root.addStretch()
        self.setLayout(root)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    # ------------------------------------------------------------------
    def _build_header_section(self) -> QFrame:
        builder = self._build_pitcher_header if self._is_pitcher else self._build_hitter_header
        widget = builder()
        if widget is None:
            widget = self._build_generic_header()
        return widget

    def _build_hitter_header(self) -> QFrame | None:
        frame = QFrame()
        frame.setObjectName("ProfileHeader")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(18)

        header_row.addWidget(self._build_avatar_panel(), 0)
        header_row.addWidget(self._build_hitter_identity_block(), 2)
        header_row.addWidget(self._build_overall_block(), 1)
        header_row.addWidget(self._build_fielding_block(), 1)

        outer.addLayout(header_row)
        outer.addWidget(self._build_scouting_summary_box())
        return frame

    def _build_hitter_identity_block(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        name = QLabel(f"{self.player.first_name} {self.player.last_name}")
        name.setObjectName("PlayerName")
        name.setProperty("profile", "name")
        layout.addWidget(name, 0, 0, 1, 2)

        age = self._calculate_age(self.player.birthdate)
        layout.addWidget(QLabel(f"Age: {age}"), 1, 0)
        layout.addWidget(QLabel(f"Bats: {getattr(self.player, 'bats', '?')}"), 1, 1)
        layout.addWidget(QLabel(f"Height: {self._format_height(getattr(self.player, 'height', None))}"), 2, 0)
        layout.addWidget(QLabel(f"Weight: {getattr(self.player, 'weight', '?')}"), 2, 1)

        positions = [self.player.primary_position, *getattr(self.player, 'other_positions', [])]
        positions = [p for p in positions if p]
        pos_label = ', '.join(positions) if positions else '?'
        layout.addWidget(QLabel(f"Positions: {pos_label}"), 3, 0, 1, 2)

        layout.addWidget(QLabel(f"Groundball/Flyball: {getattr(self.player, 'gf', '?')}"), 4, 0, 1, 2)
        return panel

    def _build_overall_block(self, *, title: str = "Overall", overall: int | None = None) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("OverallBlock")
        wrapper.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        header = QLabel(title)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        overall_val = overall if overall is not None else getattr(self.player, 'overall', None)
        if not isinstance(overall_val, (int, float)):
            overall_val = self._estimate_overall_rating()

        overall_label = QLabel(str(int(round(overall_val))) if isinstance(overall_val, (int, float)) else str(overall_val))
        overall_label.setObjectName("OverallValue")
        overall_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(overall_label)

        return wrapper

    def _build_fielding_block(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("FieldingBlock")
        wrapper.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        title = QLabel("Defense")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        diagram = QLabel()
        diagram.setAlignment(Qt.AlignmentFlag.AlignCenter)
        diagram.setObjectName("FieldDiagram")
        pix = self._load_field_diagram_pixmap()
        if pix is not None:
            scaled = pix.scaled(
                160,
                130,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            diagram.setPixmap(scaled)
        else:
            diagram.setText("Field Chart")
            diagram.setMinimumSize(160, 130)
        layout.addWidget(diagram)

        metrics = QWidget()
        grid = QGridLayout(metrics)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)

        metric_pairs = [
            ("Fielding", getattr(self.player, 'fa', '?')),
            ("Arm", getattr(self.player, 'arm', '?')),
            ("Speed", getattr(self.player, 'sp', '?')),
        ]
        for row, (label, value) in enumerate(metric_pairs):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(QLabel(str(value)), row, 1)

        layout.addWidget(metrics)
        return wrapper

    def _build_scouting_summary_box(self) -> QWidget:
        box = QFrame()
        box.setObjectName("ScoutingBox")
        box.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        summary = getattr(self.player, 'summary', '') or "No scouting report available."
        label = QLabel(summary)
        label.setWordWrap(True)
        layout.addWidget(label)
        return box

    def _build_pitcher_header(self) -> QFrame | None:
        frame = QFrame()
        frame.setObjectName("ProfileHeader")

        outer = QVBoxLayout(frame)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(18)

        header_row.addWidget(self._build_avatar_panel(), 0)
        header_row.addWidget(self._build_pitcher_identity_block(), 2)
        header_row.addWidget(self._build_overall_block(), 1)
        header_row.addWidget(self._build_pitcher_arsenal_block(), 1)

        outer.addLayout(header_row)
        outer.addWidget(self._build_pitcher_summary_box())
        return frame

    def _build_pitcher_identity_block(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        name = QLabel(f"{self.player.first_name} {self.player.last_name}")
        name.setObjectName("PlayerName")
        name.setProperty("profile", "name")
        layout.addWidget(name, 0, 0, 1, 2)

        age = self._calculate_age(self.player.birthdate)
        role = getattr(self.player, 'role', '') or 'Pitcher'
        layout.addWidget(QLabel(f"Age: {age}"), 1, 0)
        layout.addWidget(QLabel(f"Role: {role}"), 1, 1)

        bats = getattr(self.player, 'bats', '?')
        gf = getattr(self.player, 'gf', '?')
        layout.addWidget(QLabel(f"Bats: {bats}"), 2, 0)
        layout.addWidget(QLabel(f"GF: {gf}"), 2, 1)

        control = getattr(self.player, 'control', '?')
        movement = getattr(self.player, 'movement', '?')
        layout.addWidget(QLabel(f"Control: {control}"), 3, 0)
        layout.addWidget(QLabel(f"Movement: {movement}"), 3, 1)

        endurance = getattr(self.player, 'endurance', '?')
        hold_runner = getattr(self.player, 'hold_runner', '?')
        layout.addWidget(QLabel(f"Endurance: {endurance}"), 4, 0)
        layout.addWidget(QLabel(f"Hold Runner: {hold_runner}"), 4, 1)
        return panel

    def _build_pitcher_arsenal_block(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("ArsenalBlock")
        wrapper.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QGridLayout(wrapper)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        title = QLabel("Pitch Arsenal")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 2)

        pitch_labels = {
            'fb': 'Fastball',
            'si': 'Sinker',
            'sl': 'Slider',
            'cu': 'Changeup',
            'cb': 'Curveball',
            'scb': 'Screwball',
            'kn': 'Knuckle',
        }
        values = []
        for key, label in pitch_labels.items():
            value = getattr(self.player, key, None)
            if isinstance(value, (int, float)) and value > 0:
                values.append((label, int(value)))
        if not values:
            layout.addWidget(QLabel("No pitch data"), 1, 0, 1, 2)
            return wrapper

        max_value = max(v for _, v in values)
        for idx, (label, value) in enumerate(values, start=1):
            row = idx
            layout.addWidget(QLabel(label), row, 0)
            value_label = QLabel(str(value))
            if value == max_value:
                value_label.setProperty("highlight", True)
            layout.addWidget(value_label, row, 1)

        return wrapper

    def _build_pitcher_summary_box(self) -> QWidget:
        box = self._build_scouting_summary_box()
        layout = box.layout()
        if layout is not None:
            fatigue = getattr(self.player, 'fatigue', '').replace('_', ' ').title()
            fatigue_text = fatigue or 'Fresh'
            layout.addWidget(QLabel(f"Fatigue: {fatigue_text}"))
            if getattr(self.player, 'injured', False):
                desc = getattr(self.player, 'injury_description', 'Injured') or 'Injured'
                layout.addWidget(QLabel(f"Injury: {desc}"))
        return box

    def _build_generic_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ProfileHeader")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)
        outer.addWidget(section_title("Player Profile"))

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(18)

        body_layout.addWidget(self._build_avatar_panel(), 0)
        body_layout.addWidget(self._build_identity_panel(), 1)
        body_layout.addWidget(self._build_role_panel(), 1)

        outer.addWidget(body)
        return frame


    def _load_avatar_pixmap(self) -> QPixmap:
        pix = QPixmap(f"images/avatars/{self.player.player_id}.png")
        if pix.isNull():
            pix = QPixmap("images/avatars/default.png")
        if pix.isNull():
            placeholder = QPixmap(128, 128)
            placeholder.fill(Qt.GlobalColor.darkGray)
            return placeholder
        return pix.scaled(
            128,
            128,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _load_field_diagram_pixmap(self) -> QPixmap | None:
        if PlayerProfileDialog._FIELD_DIAGRAM_CACHE is None:
            path = get_base_dir() / "assets" / "field_diagram.png"
            if path.exists():
                PlayerProfileDialog._FIELD_DIAGRAM_CACHE = QPixmap(str(path))
        return PlayerProfileDialog._FIELD_DIAGRAM_CACHE

    def _build_avatar_panel(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        avatar_label = QLabel()
        pix = self._load_avatar_pixmap()
        if not pix.isNull():
            avatar_label.setPixmap(pix)
        avatar_label.setFixedSize(128, 128)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        layout.addStretch()
        return wrapper

    def _build_identity_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        name = QLabel(f"{self.player.first_name} {self.player.last_name}")
        name.setObjectName("PlayerName")
        layout.addWidget(name)

        age = self._calculate_age(self.player.birthdate)
        info_lines = [
            f"Age: {age}",
            f"Height: {self._format_height(getattr(self.player, 'height', None))}",
            f"Weight: {getattr(self.player, 'weight', '?')}",
            f"Bats: {getattr(self.player, 'bats', '?')}",
        ]
        positions = [self.player.primary_position, *getattr(self.player, 'other_positions', [])]
        positions = [p for p in positions if p]
        if positions:
            info_lines.append("Positions: " + ", ".join(positions))
        for line in info_lines:
            layout.addWidget(QLabel(line))

        layout.addStretch()
        return panel

    def _build_role_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if self._is_pitcher:
            role = getattr(self.player, 'role', '') or 'Pitcher'
            layout.addWidget(QLabel(f"Role: {role}"))
            layout.addWidget(QLabel(f"GF: {getattr(self.player, 'gf', '?')}"))
        else:
            layout.addWidget(QLabel(f"Primary: {self.player.primary_position}"))
            others = [p for p in getattr(self.player, 'other_positions', []) if p]
            if others:
                layout.addWidget(QLabel("Other: " + ", ".join(others)))
            layout.addWidget(QLabel(f"GF: {getattr(self.player, 'gf', '?')}"))

        layout.addStretch()
        return panel

    def _build_overview_section(self) -> QWidget | None:
        ratings = self._collect_ratings()
        if not ratings:
            return None

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

    def _create_stats_table(self, rows: List[Tuple[str, Dict[str, Any]]], columns: List[str]) -> QTableWidget:
        table = QTableWidget(len(rows), len(columns) + 1)
        table.setObjectName("StatsTable")
        headers = ["Year"] + [c.upper() for c in columns]
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row_idx, (year, data) in enumerate(rows):
            label_lower = str(year).lower()
            if "career" in label_lower:
                row_role = "career"
            elif "current" in label_lower:
                row_role = "current"
            else:
                row_role = "history"

            year_item = self._stat_item(year, align_left=True)
            year_item.setData(Qt.ItemDataRole.UserRole, row_role)
            table.setItem(row_idx, 0, year_item)

            for col_idx, key in enumerate(columns, start=1):
                value = data.get(key, "")
                item = self._stat_item(value)
                item.setData(Qt.ItemDataRole.UserRole, row_role)
                table.setItem(row_idx, col_idx, item)
        table.setSortingEnabled(True)
        return table

    def _create_stats_summary(self, rows: List[Tuple[str, Dict[str, Any]]], columns: List[str]) -> QWidget | None:
        target = None
        for label, data in rows:
            if label.lower() == "career" and data:
                target = data
                break
        if target is None and rows:
            target = rows[-1][1]
        if not target:
            return None

        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        display_columns = columns[:6]
        for idx, key in enumerate(display_columns):
            label = QLabel(key.upper())
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            value = QLabel(self._format_stat(target.get(key, "")))
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(label, idx, 0)
            grid.addWidget(value, idx, 1)
        return panel

    def _build_stat_key_footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("StatFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Stat Key:"))
        chips = [
            ("Current Season", "current"),
            ("Career Totals", "career"),
            ("History", "history"),
        ]
        for text, variant in chips:
            chip = QLabel(text)
            chip.setObjectName("StatChip")
            chip.setProperty("variant", variant)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setMinimumWidth(90)
            chip.setMargin(4)
            layout.addWidget(chip)
        layout.addStretch()
        return footer

    def _estimate_overall_rating(self) -> int:
        if self._is_pitcher:
            keys = [
                "endurance",
                "control",
                "movement",
                "hold_runner",
                "arm",
                "fa",
                "fb",
                "cu",
                "cb",
                "sl",
                "si",
                "scb",
                "kn",
            ]
        else:
            keys = [
                "ch",
                "ph",
                "sp",
                "pl",
                "vl",
                "sc",
                "fa",
                "arm",
                "gf",
            ]
        values = [getattr(self.player, key, 0) for key in keys]
        numeric = [v for v in values if isinstance(v, (int, float))]
        if not numeric:
            return 0
        return max(0, min(99, int(round(sum(numeric) / len(numeric)))))

    def _estimate_peak_rating(self) -> int:
        potential = getattr(self.player, 'potential', {}) or {}
        if not potential:
            return self._estimate_overall_rating()
        if self._is_pitcher:
            keys = [
                "control",
                "movement",
                "endurance",
                "hold_runner",
                "arm",
                "fa",
                "fb",
                "cu",
                "cb",
                "sl",
                "si",
                "scb",
                "kn",
            ]
        else:
            keys = [
                "ch",
                "ph",
                "sp",
                "pl",
                "vl",
                "sc",
                "fa",
                "arm",
                "gf",
            ]
        values = [potential.get(key, getattr(self.player, key, 0)) for key in keys]
        numeric = [v for v in values if isinstance(v, (int, float))]
        if not numeric:
            return self._estimate_overall_rating()
        return max(0, min(99, int(round(sum(numeric) / len(numeric)))))

    def _build_stats_section(self, rows: List[Tuple[str, Dict[str, Any]]]) -> Card:
        card = Card()
        layout = card.layout()
        layout.addWidget(section_title("Stats"))

        if not rows:
            layout.addWidget(QLabel("No stats available"))
            return card

        columns = _PITCHING_STATS if self._is_pitcher else _BATTING_STATS

        tabs = QTabWidget()
        tabs.setObjectName("StatsTabs")
        primary_label = "Pitching" if self._is_pitcher else "Batting"
        tabs.addTab(self._create_stats_table(rows, columns), primary_label)

        summary = self._create_stats_summary(rows, columns)
        if summary is not None:
            tabs.addTab(summary, "Summary")

        layout.addWidget(tabs)
        layout.addWidget(self._build_stat_key_footer())
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
            "is_pitcher",
        }
        values: Dict[str, Any] = {}
        for key, val in vars(self.player).items():
            if key in excluded or key.startswith("pot_"):
                continue
            if isinstance(val, (int, float)):
                values[key] = val

        if self._is_pitcher:
            ordered: Dict[str, Any] = {}
            pitcher_sequence = [
                ("arm", "AS"),
                ("endurance", "EN"),
                ("control", "CO"),
                ("fb", "FB"),
                ("sl", "SL"),
                ("cu", "CU"),
                ("cb", "CB"),
                ("si", "SI"),
                ("scb", "SCB"),
                ("kn", "KN"),
                ("movement", "MO"),
                ("fa", "FA"),
            ]
            for key, label in pitcher_sequence:
                if key in values:
                    ordered[label] = values.pop(key)
            for key in sorted(values):
                ordered[self._format_rating_label(key)] = values[key]
            return ordered

        ordered: Dict[str, Any] = {}
        hitter_sequence = [
            ("ch", "CH"),
            ("ph", "PH"),
            ("sp", "SP"),
            ("fa", "FA"),
            ("arm", "AS"),
        ]
        for key, label in hitter_sequence:
            if key in values:
                ordered[label] = values.pop(key)
        for key in sorted(values):
            ordered[self._format_rating_label(key)] = values[key]
        return ordered

    def _format_rating_label(self, key: str) -> str:
        if "_" in key:
            return key.replace("_", " ").title()
        if len(key) <= 3:
            return key.upper()
        return key.title()

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

