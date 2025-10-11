"""Dialog for displaying a player profile with themed styling."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
import sys
import csv
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

try:
    from PyQt6.QtCore import Qt, QPointF, QRectF
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
    QPointF = SimpleNamespace

try:
    from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QPolygonF
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

    class _GraphicDummy:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __getattr__(self, name):  # noqa: D401 - simple no-op forwarder
            def _noop(*_args, **_kwargs) -> None:
                return None

            return _noop

    QColor = QPainter = QPen = QBrush = QPolygonF = _GraphicDummy

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
        QPushButton,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QSizePolicy,
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
from utils.player_loader import load_players_from_csv
from .components import Card, section_title


HEADLESS_QT = getattr(QDialog, "__name__", "").lower().startswith("_qt")


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
        # Ensure the view reflects the latest persisted season stats in case
        # the passed ``player`` instance is stale in memory while simulations
        # are running in another window.
        try:
            from utils.stats_persistence import load_stats as _load_season
            data = _load_season()
            cur = data.get("players", {}).get(player.player_id)
            if isinstance(cur, dict) and cur:
                self.player.season_stats = cur
        except Exception:
            pass
        try:
            self._stats_snapshot = load_stats()
        except Exception:
            self._stats_snapshot = {}
        self._history_override = list(self._stats_snapshot.get("history", []) or [])
        self.setWindowTitle(f"{player.first_name} {player.last_name}")

        self._is_pitcher = getattr(player, "is_pitcher", False)
        self._comparison_player: Optional[Any] = None
        self._player_pool: Optional[Dict[str, Any]] = None
        self._compare_button: Optional[QPushButton] = None
        self._clear_compare_button: Optional[QPushButton] = None
        self._spray_chart_widget: Optional['SprayChartWidget'] = None
        self._rolling_stats_widget: Optional['RollingStatsWidget'] = None
        self._stats_cache: Optional[Dict[str, Any]] = None
        self._comparison_labels: Dict[str, Tuple[Any, Any]] = {}
        self._comparison_name_label: Optional[QLabel] = None

        root = QVBoxLayout()
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        if HEADLESS_QT:
            stats_history = self._collect_stats_history()
            if stats_history:
                columns = _PITCHING_STATS if self._is_pitcher else _BATTING_STATS
                self._create_stats_table(stats_history, columns)
            return

        header = self._build_header_section()
        root.addWidget(header)

        self._comparison_panel = self._build_comparison_panel()
        root.addWidget(self._comparison_panel)
        self._comparison_panel.hide()

        overview = self._build_overview_section()
        if overview is not None:
            root.addWidget(overview)

        insights = self._build_insights_section()
        if insights is not None:
            root.addWidget(insights)

        stats_history = self._collect_stats_history()
        root.addWidget(self._build_stats_section(stats_history))

        root.addStretch()
        self.setLayout(root)
        self._update_comparison_panel()
        # Size policy: provide a generous default width so headers and row titles
        # are visible without manual column resizing, but still allow the user to
        # resize the window larger if desired.
        # Size policy: robust against test stubs without real Qt widgets
        try:
            self.adjustSize()
            hint = self.sizeHint()
            # width/height may be callables on real QSize; guard for stubs
            w_attr = getattr(hint, "width", 0)
            h_attr = getattr(hint, "height", 0)
            w = int(w_attr() if callable(w_attr) else w_attr or 0)
            h = int(h_attr() if callable(h_attr) else h_attr or 0)
            min_w = max(w, 1200)
            min_h = max(h, 720)
            self.setMinimumSize(min_w, min_h)
            self.resize(min_w, min_h)
        except Exception:
            # Fallback in headless test stubs
            pass

    # ------------------------------------------------------------------
    def _build_header_section(self) -> QFrame:
        builder = self._build_pitcher_header if self._is_pitcher else self._build_hitter_header
        widget = builder()
        if widget is None:
            widget = self._build_generic_header()
        return widget

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
        layout.addWidget(
            avatar_label,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        layout.addStretch()
        return wrapper

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
        outer.addWidget(self._build_header_actions())
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
        outer.addWidget(self._build_header_actions())
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
        outer.addWidget(self._build_header_actions())
        return frame

    def _build_header_actions(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addStretch()

        compare_btn = QPushButton("Compare...")
        compare_btn.setObjectName("SecondaryButton")
        compare_btn.clicked.connect(self._prompt_comparison_player)
        layout.addWidget(compare_btn)

        clear_btn = QPushButton("Clear Compare")
        clear_btn.setObjectName("SecondaryButton")
        clear_btn.clicked.connect(self._clear_comparison)
        clear_btn.hide()
        layout.addWidget(clear_btn)

        self._compare_button = compare_btn
        self._clear_compare_button = clear_btn
        return bar


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

    def _get_stats_cache(self) -> Dict[str, Any]:
        if self._stats_cache is None:
            try:
                self._stats_cache = load_stats().get("players", {})
            except Exception:
                self._stats_cache = {}
        return self._stats_cache

    def _attach_player_stats(self, player: Any) -> None:
        if getattr(player, "season_stats", None):
            return
        try:
            stats = self._get_stats_cache().get(getattr(player, "player_id", None))
            if stats:
                player.season_stats = stats
        except Exception:
            pass

    def _player_stats(self, player: Any) -> Dict[str, Any]:
        stats = getattr(player, "season_stats", None)
        if isinstance(stats, dict):
            return stats
        return {}

    def _player_display_name(self, player: Any) -> str:
        first = str(getattr(player, "first_name", "").strip())
        last = str(getattr(player, "last_name", "").strip())
        pid = str(getattr(player, "player_id", "--"))
        full = " ".join(part for part in (first, last) if part)
        return f"{full} [{pid}]" if full else pid

    def _load_player_pool(self) -> Dict[str, Any]:
        if self._player_pool is None:
            try:
                players = load_players_from_csv("data/players.csv")
            except Exception:
                players = []
            self._player_pool = {p.player_id: p for p in players if getattr(p, "player_id", None)}
        return self._player_pool

    def _build_comparison_panel(self) -> Card:
        card = Card()
        layout = card.layout()
        layout.addWidget(section_title("Comparison"))

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        header_label = QLabel("Metric")
        header_label.setStyleSheet("font-weight:600;")
        grid.addWidget(header_label, 0, 0)
        primary_name = QLabel(self._player_display_name(self.player))
        primary_name.setStyleSheet("font-weight:600;")
        self._comparison_name_label = QLabel("--")
        self._comparison_name_label.setStyleSheet("font-weight:600;")
        grid.addWidget(primary_name, 0, 1)
        grid.addWidget(self._comparison_name_label, 0, 2)

        for idx, (metric_id, label) in enumerate(self._comparison_metric_definitions(), start=1):
            title = QLabel(label)
            grid.addWidget(title, idx, 0)
            primary_label = QLabel("--")
            compare_label = QLabel("--")
            grid.addWidget(primary_label, idx, 1)
            grid.addWidget(compare_label, idx, 2)
            self._comparison_labels[metric_id] = (primary_label, compare_label)

        layout.addLayout(grid)
        layout.addStretch()
        return card


    def _comparison_metric_definitions(self) -> List[tuple[str, str]]:
        if self._is_pitcher:
            return [
                ("overall", "Overall"),
                ("era", "ERA"),
                ("whip", "WHIP"),
                ("k9", "K/9"),
                ("bb9", "BB/9"),
                ("velocity", "Velocity"),
                ("control", "Control"),
                ("movement", "Movement"),
                ("endurance", "Endurance"),
            ]
        return [
            ("overall", "Overall"),
            ("avg", "AVG"),
            ("ops", "OPS"),
            ("hr", "HR"),
            ("rbi", "RBI"),
            ("speed", "Speed"),
            ("power", "Power"),
            ("contact", "Contact"),
            ("defense", "Defense"),
        ]

    def _metric_value(self, player: Any, metric_id: str) -> str:
        if player is None:
            return "--"
        stats = self._player_stats(player)
        def safe(key: str) -> float:
            value = stats.get(key, 0)
            try:
                return float(value or 0)
            except Exception:
                return 0.0

        if metric_id == "overall":
            value = getattr(player, "overall", None)
            if not isinstance(value, (int, float)):
                value = self._estimate_overall_rating() if player is self.player else getattr(player, "overall", "--")
            return f"{int(value)}" if isinstance(value, (int, float)) else str(value)
        if metric_id == "avg":
            ab = safe("ab")
            hits = safe("h")
            return f"{hits / ab:.3f}" if ab else "--"
        if metric_id == "ops":
            obp = self._calculate_obp(stats)
            slg = self._calculate_slg(stats)
            total = obp + slg
            return f"{total:.3f}" if total else "--"
        if metric_id == "hr":
            hr = stats.get("hr")
            return str(int(hr)) if isinstance(hr, (int, float)) else "--"
        if metric_id == "rbi":
            rbi = stats.get("rbi")
            return str(int(rbi)) if isinstance(rbi, (int, float)) else "--"
        if metric_id == "speed":
            return str(getattr(player, "sp", getattr(player, "speed", "--")))
        if metric_id == "power":
            return str(getattr(player, "ph", getattr(player, "power", "--")))
        if metric_id == "contact":
            return str(getattr(player, "ch", getattr(player, "contact", "--")))
        if metric_id == "defense":
            return str(getattr(player, "fa", getattr(player, "defense", "--")))
        if metric_id == "era":
            outs = safe("outs")
            ip = outs / 3 if outs else 0
            er = safe("er")
            return f"{(er * 9) / ip:.2f}" if ip else "--"
        if metric_id == "whip":
            outs = safe("outs")
            ip = outs / 3 if outs else 0
            if not ip:
                return "--"
            bb = safe("bb")
            hits = safe("h")
            return f"{(bb + hits) / ip:.2f}"
        if metric_id == "k9":
            outs = safe("outs")
            ip = outs / 3 if outs else 0
            if not ip:
                return "--"
            so = safe("so")
            return f"{(so * 9) / ip:.2f}"
        if metric_id == "bb9":
            outs = safe("outs")
            ip = outs / 3 if outs else 0
            if not ip:
                return "--"
            walk = safe("bb")
            return f"{(walk * 9) / ip:.2f}"
        return str(getattr(player, metric_id, "--"))

    def _build_insights_section(self) -> Card | None:
        spray_points = self._compute_spray_points()
        rolling = self._compute_rolling_stats()
        if not spray_points and not rolling.get("dates"):
            return None

        card = Card()
        layout = card.layout()
        layout.addWidget(section_title("Advanced Insights"))

        tabs = QTabWidget()
        self._spray_chart_widget = SprayChartWidget()
        self._spray_chart_widget.set_points(spray_points)
        tabs.addTab(self._spray_chart_widget, "Spray Chart")

        self._rolling_stats_widget = RollingStatsWidget()
        self._rolling_stats_widget.update_series(rolling)
        tabs.addTab(self._rolling_stats_widget, "Rolling Stats")

        layout.addWidget(tabs)
        layout.addStretch()
        return card

    def _compute_spray_points(self) -> List[Dict[str, float]]:
        stats = self._player_stats(self.player)
        singles = int(stats.get("b1", 0) or 0)
        doubles = int(stats.get("b2", 0) or 0)
        triples = int(stats.get("b3", 0) or 0)
        homers = int(stats.get("hr", 0) or 0)
        total = singles + doubles + triples + homers
        if total <= 0:
            return []

        handed = str(getattr(self.player, "bats", "R")).upper() or "R"
        if handed.startswith("L"):
            side = 1.0
        elif handed.startswith("S"):
            side = 0.0
        else:
            side = -1.0

        points: List[Dict[str, float]] = []

        def add_points(count: int, base_x: float, depth: float, spread: float, kind: str) -> None:
            for idx in range(int(count)):
                seed = hash((self.player.player_id, kind, idx))
                offset = ((seed % 1000) / 999.0) - 0.5
                if side == 0.0:
                    x = base_x + offset * spread
                    if idx % 2 == 0:
                        x *= -1
                else:
                    x = (base_x * side) + offset * spread
                x = max(-0.95, min(0.95, x))
                depth_variation = ((seed // 1000) % 200) / 1000.0 - 0.1
                y = max(0.1, min(1.0, depth + depth_variation))
                points.append({"x": x, "y": y, "kind": kind})

        add_points(singles, 0.45, 0.35, 0.25, "1B")
        add_points(doubles, 0.25, 0.60, 0.20, "2B")
        add_points(triples, 0.05, 0.80, 0.20, "3B")
        add_points(homers, 0.00, 1.00, 0.15, "HR")
        return points

    def _compute_rolling_stats(self) -> Dict[str, Any]:
        history_dir = get_base_dir() / "data" / "season_history"
        if not history_dir.exists():
            return {"dates": [], "series": {}}

        snapshots = sorted(history_dir.glob("*.json"))
        dates: List[str] = []
        series: Dict[str, List[float]] = {}
        if self._is_pitcher:
            metric_specs = [("ERA", "era"), ("WHIP", "whip")]
        else:
            metric_specs = [("AVG", "avg"), ("OPS", "ops")]
        for label, _ in metric_specs:
            series[label] = []

        for path in snapshots[-12:]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            stats = payload.get("players", {}).get(self.player.player_id)
            if not stats:
                continue
            dates.append(path.stem)
            temp_stats = stats
            for label, metric_id in metric_specs:
                if metric_id == "avg":
                    ab = float(temp_stats.get("ab", 0) or 0)
                    hits = float(temp_stats.get("h", 0) or 0)
                    value = hits / ab if ab else 0.0
                elif metric_id == "ops":
                    value = self._calculate_obp(temp_stats) + self._calculate_slg(temp_stats)
                elif metric_id == "era":
                    outs = float(temp_stats.get("outs", 0) or 0)
                    ip = outs / 3 if outs else 0.0
                    er = float(temp_stats.get("er", 0) or 0)
                    value = (er * 9) / ip if ip else 0.0
                elif metric_id == "whip":
                    outs = float(temp_stats.get("outs", 0) or 0)
                    ip = outs / 3 if outs else 0.0
                    walks = float(temp_stats.get("bb", 0) or 0)
                    hits_allowed = float(temp_stats.get("h", 0) or 0)
                    value = (walks + hits_allowed) / ip if ip else 0.0
                else:
                    value = 0.0
                series[label].append(round(value, 3))

        return {"dates": dates, "series": series}


    def _prompt_comparison_player(self) -> None:
        pool = self._load_player_pool().copy()
        selector = ComparisonSelectorDialog(pool, self.player.player_id, self)
        if selector.exec():
            chosen = selector.selected_player
            if chosen is None:
                return
            self._attach_player_stats(chosen)
            self._comparison_player = chosen
            self._update_comparison_panel()

    def _clear_comparison(self) -> None:
        self._comparison_player = None
        self._update_comparison_panel()

    def _update_comparison_panel(self) -> None:
        has_compare = self._comparison_player is not None
        if self._comparison_name_label is not None:
            name = self._player_display_name(self._comparison_player) if has_compare else "--"
            self._comparison_name_label.setText(name)
        for metric_id, _ in self._comparison_metric_definitions():
            labels = self._comparison_labels.get(metric_id)
            if not labels:
                continue
            primary_label, compare_label = labels
            primary_label.setText(self._metric_value(self.player, metric_id))
            compare_label.setText(self._metric_value(self._comparison_player, metric_id) if has_compare else "--")
        if self._comparison_panel is not None:
            if has_compare:
                self._comparison_panel.show()
                if self._clear_compare_button is not None:
                    self._clear_compare_button.show()
            else:
                self._comparison_panel.hide()
                if self._clear_compare_button is not None:
                    self._clear_compare_button.hide()

    def _calculate_obp(self, stats: Dict[str, Any]) -> float:
        h = float(stats.get("h", 0) or 0)
        bb = float(stats.get("bb", 0) or 0)
        hbp = float(stats.get("hbp", 0) or 0)
        ab = float(stats.get("ab", 0) or 0)
        sf = float(stats.get("sf", 0) or 0)
        denom = ab + bb + hbp + sf
        if denom <= 0:
            return 0.0
        return (h + bb + hbp) / denom

    def _calculate_slg(self, stats: Dict[str, Any]) -> float:
        ab = float(stats.get("ab", 0) or 0)
        if ab <= 0:
            return 0.0
        singles = float(stats.get("b1", 0) or 0)
        doubles = float(stats.get("b2", 0) or 0)
        triples = float(stats.get("b3", 0) or 0)
        homers = float(stats.get("hr", 0) or 0)
        total_bases = singles + (2 * doubles) + (3 * triples) + (4 * homers)
        return total_bases / ab


class SprayChartWidget(QWidget):
    """Draw a simple spray chart using normalized hit locations."""

    def __init__(self) -> None:
        super().__init__()
        self._points: List[Dict[str, float]] = []
        self.setMinimumHeight(220)

    def set_points(self, points: List[Dict[str, float]] | None) -> None:
        self._points = points or []
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        except Exception:
            pass
        rect = self.rect().adjusted(20, 20, -20, -20)
        home_x = rect.left() + rect.width() / 2
        home_y = rect.bottom()

        painter.setPen(QPen(QColor("#adb5bd"), 2))
        painter.drawLine(int(home_x), int(home_y), rect.left(), rect.top())
        painter.drawLine(int(home_x), int(home_y), rect.right(), rect.top())

        arc_rect = QRectF(rect.left(), rect.top() - rect.height(), rect.width(), rect.height() * 2)
        painter.drawArc(arc_rect, 0, 180 * 16)

        color_map = {
            "1B": QColor("#51cf66"),
            "2B": QColor("#339af0"),
            "3B": QColor("#fcc419"),
            "HR": QColor("#fa5252"),
        }

        radius_x = rect.width() / 2
        radius_y = rect.height()
        for point in self._points:
            x_norm = float(point.get("x", 0))
            y_norm = float(point.get("y", 0))
            kind = str(point.get("kind", "1B"))
            color = color_map.get(kind, QColor("#868e96"))
            x = home_x + x_norm * radius_x
            y = home_y - y_norm * radius_y
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color))
            painter.drawEllipse(QPointF(x, y), 5, 5)

        if not self._points:
            painter.setPen(QPen(QColor("#868e96")))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No batted ball data available.",
            )
        painter.end()


class RollingStatsWidget(QWidget):
    """Line chart displaying rolling metrics such as AVG/OPS or ERA/WHIP."""

    palette = [
        QColor("#228be6"),
        QColor("#f76707"),
        QColor("#12b886"),
        QColor("#fa5252"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._dates: List[str] = []
        self._series: Dict[str, List[float]] = {}
        self.setMinimumHeight(220)

    def update_series(self, data: Dict[str, Any]) -> None:
        self._dates = list(data.get("dates", []))
        raw_series = data.get("series", {}) or {}
        self._series = {label: list(values) for label, values in raw_series.items()}
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        except Exception:
            pass
        rect = self.rect().adjusted(20, 20, -20, -40)

        values: List[float] = []
        for series in self._series.values():
            values.extend(float(v) for v in series)
        values = [v for v in values if v or v == 0.0]

        if not self._dates or not values:
            painter.setPen(QPen(QColor("#868e96")))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No rolling data available.",
            )
            painter.end()
            return

        min_val = min(values)
        max_val = max(values)
        if abs(max_val - min_val) < 0.001:
            max_val += 0.5
            min_val -= 0.5

        painter.setPen(QPen(QColor("#adb5bd")))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.bottomLeft(), rect.topLeft())

        step = rect.width() / max(1, len(self._dates) - 1)

        def map_y(value: float) -> float:
            if max_val == min_val:
                return rect.bottom()
            ratio = (value - min_val) / (max_val - min_val)
            return rect.bottom() - ratio * rect.height()

        for idx, (label, series) in enumerate(self._series.items()):
            if not series:
                continue
            points = [
                QPointF(rect.left() + index * step, map_y(float(value)))
                for index, value in enumerate(series)
            ]
            pen = QPen(self.palette[idx % len(self.palette)], 2)
            painter.setPen(pen)
            painter.drawPolyline(QPolygonF(points))
            painter.setPen(QPen(self.palette[idx % len(self.palette)]))
            painter.drawText(
                rect.left() + 8 + idx * 90,
                rect.top() - 8,
                f"{label}",
            )

        painter.setPen(QPen(QColor("#495057")))
        painter.drawText(
            rect.left(),
            rect.bottom() + 18,
            self._dates[0],
        )
        if len(self._dates) > 1:
            painter.drawText(
                rect.right() - 60,
                rect.bottom() + 18,
                self._dates[-1],
            )
        painter.end()


class ComparisonSelectorDialog(QDialog):
    """Simple selector to choose a comparison player from the league."""

    def __init__(self, pool: Dict[str, Any], exclude_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Comparison Player")
        self._players = [
            player for pid, player in pool.items() if pid and pid != exclude_id
        ]
        self._players.sort(
            key=lambda p: (
                str(getattr(p, "last_name", "")).lower(),
                str(getattr(p, "first_name", "")).lower(),
            )
        )
        self._selected: Any | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Search by name or player ID"))

        self.search_edit = QLineEdit()
        layout.addWidget(self.search_edit)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.compare_button = QPushButton("Compare")
        self.cancel_button = QPushButton("Cancel")
        button_row.addWidget(self.compare_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

        self.search_edit.textChanged.connect(self._apply_filter)
        self.compare_button.clicked.connect(self._accept_selection)
        self.cancel_button.clicked.connect(self.reject)
        self.list_widget.itemDoubleClicked.connect(lambda *_: self._accept_selection())

        self._apply_filter("")

    def _apply_filter(self, text: str) -> None:
        query = text.strip().lower()
        self.list_widget.clear()
        for player in self._players:
            label = self._display_label(player)
            if query and query not in label.lower():
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, player)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _display_label(self, player: Any) -> str:
        name = " ".join(
            part
            for part in (
                str(getattr(player, "first_name", "")).strip(),
                str(getattr(player, "last_name", "")).strip(),
            )
            if part
        )
        pid = getattr(player, "player_id", "--")
        pos = getattr(player, "primary_position", "?")
        return f"{name or pid} ({pos}) [{pid}]"

    def _accept_selection(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        player = item.data(Qt.ItemDataRole.UserRole)
        if player is None:
            return
        self._selected = player
        self.accept()

    @property
    def selected_player(self) -> Any | None:
        return self._selected

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
        # Make the first column (Year/range labels) fit its text while the
        # remaining columns stretch to fill the available space.
        header = table.horizontalHeader()
        try:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        except Exception:
            pass

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
        try:
            year_label = QLabel(f"Season Year: {self._current_season_year():04d}")
            layout.addWidget(year_label)
        except Exception:
            pass

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
        """Return rows for the stats table.

        Includes current season and career rows when available. If no season/
        career stats exist, falls back to recent historical snapshots loaded
        from persistence, labelling undated snapshots as "Year N".
        """
        is_pitcher = getattr(self.player, "is_pitcher", False)
        rows: List[Tuple[str, Dict[str, Any]]] = []

        current_year = self._current_season_year()
        season = self._stats_to_dict(getattr(self.player, "season_stats", {}), is_pitcher)
        # Clamp displayed games to the number already played by teams this
        # season to avoid showing stale totals when starting a new season.
        if season:
            try:
                from utils.stats_persistence import load_stats as _load_season
                all_stats = _load_season()
                team_stats = all_stats.get("teams", {}) or {}
                games_list = [int(v.get("g", v.get("games", 0)) or 0) for v in team_stats.values()]
                if games_list:
                    max_team_g = max(games_list)
                    g_val = int(season.get("g", 0) or 0)
                    if max_team_g:
                        season["g"] = min(g_val, max_team_g)
            except Exception:
                pass
            rows.append((f"{current_year:04d}", season))

        history_map = getattr(self.player, "career_history", {}) or {}
        if isinstance(history_map, dict):
            history_rows: list[tuple[Tuple[int, str], str, Dict[str, Any]]] = []
            for season_id, raw_stats in history_map.items():
                data = self._stats_to_dict(raw_stats, is_pitcher)
                if not data:
                    continue
                label = self._format_season_label(str(season_id))
                history_rows.append((self._season_sort_key(season_id), label, data))
            if history_rows:
                history_rows.sort(key=lambda item: item[0], reverse=True)
                rows.extend((label, data) for _, label, data in history_rows)

        career = self._stats_to_dict(getattr(self.player, "career_stats", {}), is_pitcher)
        if career:
            rows.append(("Career", career))
        if rows:
            return rows
        # Fallback: recent snapshots either from preloaded history or canonical store.
        history_entries = list(self._history_override)[-5:] if self._history_override else []
        print("DEBUG history entries override", history_entries)
        rating_fields = getattr(type(self.player), "_rating_fields", set())
        if history_entries:
            for idx, entry in enumerate(history_entries, start=1):
                print("DEBUG entry", entry)
                player_data = entry.get("players", {}).get(self.player.player_id)
                if not player_data:
                    print("DEBUG missing player data", self.player.player_id)
                    continue
                snapshot = player_data.get("stats", player_data)
                data = self._stats_to_dict(snapshot, is_pitcher)
                if data:
                    label = entry.get("year")
                    rows.append((str(label) if label is not None else f"Year {idx}", data))
            if rows:
                return rows
        for label, _ratings, stats in self._load_history():
            is_pitcher = getattr(self.player, "is_pitcher", False)
            data = self._stats_to_dict(stats, is_pitcher)
            if data:
                rows.append((label, data))
        return rows

    def _load_history(self) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
        loader = getattr(sys.modules[__name__], "load_stats")
        data = loader()
        history: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
        rating_fields = getattr(type(self.player), "_rating_fields", set())
        entries = data.get("history", [])[-5:]
        used_years: set[str] = set()
        snap_idx = 0
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
            if year is None:
                snap_idx += 1
                year_label = f"Year {snap_idx}"
            else:
                year_label = str(year)
            if year_label in used_years:
                continue
            used_years.add(year_label)
            history.append((year_label, ratings, stats))
        return history

    def _current_season_year(self) -> int:
        """Return the current season year based on schedule/progress.

        Prefer the year of the date at the current simulation index from
        ``season_progress.json``. If unavailable, use the first scheduled
        game's year rather than the maximum to avoid multi-year schedules
        (e.g., repeated cycles) pushing the label into the future. Falls back
        to the calendar year on error.
        """
        try:
            data_dir = Path(__file__).resolve().parents[1] / "data"
            sched = data_dir / "schedule.csv"
            prog = data_dir / "season_progress.json"
            if not sched.exists():
                return datetime.now().year
            rows: list[dict] = []
            with sched.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            if not rows:
                return datetime.now().year
            # Try to read the current sim index
            idx = 0
            if prog.exists():
                try:
                    import json as _json
                    data = _json.loads(prog.read_text(encoding="utf-8"))
                    raw_idx = int(data.get("sim_index", 0) or 0)
                    idx = max(0, min(raw_idx, len(rows) - 1))
                except Exception:
                    idx = 0
            cur_date = str(rows[idx].get("date") or "").strip()
            if cur_date:
                try:
                    return int(cur_date.split("-")[0])
                except Exception:
                    pass
            # Fallback: use the first scheduled game's year
            first_date = str(rows[0].get("date") or "").strip()
            if first_date:
                try:
                    return int(first_date.split("-")[0])
                except Exception:
                    pass
            return datetime.now().year
        except Exception:
            return datetime.now().year

    @staticmethod
    def _season_year_from_id(season_id: str) -> int:
        try:
            token = str(season_id).rsplit("-", 1)[-1]
            return int(token)
        except Exception:
            return -1

    def _season_sort_key(self, season_id: str) -> tuple[int, str]:
        return (self._season_year_from_id(season_id), str(season_id))

    def _format_season_label(self, season_id: str) -> str:
        parts = str(season_id).rsplit("-", 1)
        if len(parts) == 2:
            league_token, year_token = parts
            try:
                year_int = int(year_token)
                label = f"{year_int:04d}"
            except ValueError:
                return str(season_id)
            league_token = league_token.strip().upper()
            if league_token and league_token not in {"LEAGUE"}:
                return f"{label} ({league_token})"
            return label
        return str(season_id)

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


if not hasattr(PlayerProfileDialog, '_create_stats_table'):
    def _fallback_create_stats_table(self, rows, columns):  # pragma: no cover - stub
        return None

    PlayerProfileDialog._create_stats_table = _fallback_create_stats_table  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_build_insights_section'):
    def _fallback_build_insights(self):  # pragma: no cover - stub
        return None

    PlayerProfileDialog._build_insights_section = _fallback_build_insights  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_compute_spray_points'):
    def _fallback_spray_points(self):  # pragma: no cover - stub
        return []

    PlayerProfileDialog._compute_spray_points = _fallback_spray_points  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_compute_rolling_stats'):
    def _fallback_rolling_stats(self):  # pragma: no cover - stub
        return {'dates': [], 'series': {}}

    PlayerProfileDialog._compute_rolling_stats = _fallback_rolling_stats  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_calculate_age'):
    def _fallback_calculate_age(self, birthdate_str: str):  # pragma: no cover - stub
        try:
            birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            return today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )
        except Exception:
            return "?"

    PlayerProfileDialog._calculate_age = _fallback_calculate_age  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_format_height'):
    def _fallback_format_height(self, height: Any) -> str:  # pragma: no cover - stub
        try:
            total_inches = int(height)
        except (TypeError, ValueError):
            return "?"
        feet, inches = divmod(total_inches, 12)
        return f"{feet}'{inches}\""

    PlayerProfileDialog._format_height = _fallback_format_height  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_estimate_overall_rating'):
    def _fallback_estimate_overall_rating(self) -> int:  # pragma: no cover - stub
        try:
            values = []
            if getattr(self, "_is_pitcher", False):
                keys = [
                    "endurance",
                    "control",
                    "movement",
                    "hold_runner",
                    "arm",
                    "fa", "fb", "cu", "cb", "sl", "si", "scb", "kn",
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
            for key in keys:
                val = getattr(self.player, key, None)
                if isinstance(val, (int, float)):
                    values.append(val)
            if not values:
                return 0
            return max(0, min(99, int(round(sum(values) / len(values)))))
        except Exception:
            return 0

    PlayerProfileDialog._estimate_overall_rating = _fallback_estimate_overall_rating  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_estimate_peak_rating'):
    def _fallback_estimate_peak_rating(self) -> int:  # pragma: no cover - stub
        potential = getattr(self.player, "potential", {}) or {}
        overall = potential.get("overall")
        if isinstance(overall, (int, float)):
            return int(round(overall))
        return self._estimate_overall_rating()

    PlayerProfileDialog._estimate_peak_rating = _fallback_estimate_peak_rating  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_format_rating_label'):
    def _fallback_format_rating_label(self, label: str, value: Any) -> str:  # pragma: no cover - stub
        return f"{label}: {value}"

    PlayerProfileDialog._format_rating_label = _fallback_format_rating_label  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_load_field_diagram_pixmap'):
    def _fallback_load_field_diagram_pixmap(self):  # pragma: no cover - stub
        return None

    PlayerProfileDialog._load_field_diagram_pixmap = _fallback_load_field_diagram_pixmap  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_load_avatar_pixmap'):
    def _fallback_load_avatar_pixmap(self):  # pragma: no cover - stub
        try:
            path = getattr(self.player, "avatar_path", None)
            if path:
                pix = QPixmap(str(path))
                if not pix.isNull():
                    return pix
        except Exception:
            pass
        return QPixmap()

    PlayerProfileDialog._load_avatar_pixmap = _fallback_load_avatar_pixmap  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_stats_to_dict'):
    def _fallback_stats_to_dict(self, stats: Any, is_pitcher: bool) -> Dict[str, Any]:  # pragma: no cover - stub
        if isinstance(stats, dict):
            data = dict(stats)
        elif is_dataclass(stats):
            data = asdict(stats)
        else:
            return {}
        if is_pitcher:
            return self._normalize_pitching_stats(data)
        return data

    PlayerProfileDialog._stats_to_dict = _fallback_stats_to_dict  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_normalize_pitching_stats'):
    def _fallback_normalize_pitching_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - stub
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
        return result

    PlayerProfileDialog._normalize_pitching_stats = _fallback_normalize_pitching_stats  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_format_stat'):
    def _fallback_format_stat(self, value: Any) -> str:  # pragma: no cover - stub
        try:
            return f"{float(value):.3f}"
        except Exception:
            return str(value)

    PlayerProfileDialog._format_stat = _fallback_format_stat  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_build_stats_section'):
    def _fallback_build_stats_section(self, stats_history):  # pragma: no cover - stub
        label = QLabel("Statistics unavailable.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    PlayerProfileDialog._build_stats_section = _fallback_build_stats_section  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_build_overview_section'):
    def _fallback_build_overview_section(self):  # pragma: no cover - stub
        return None

    PlayerProfileDialog._build_overview_section = _fallback_build_overview_section  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_build_comparison_panel'):
    def _fallback_build_comparison_panel(self):  # pragma: no cover - stub
        panel = QFrame()
        panel.setLayout(QVBoxLayout())
        panel.setVisible(False)
        return panel

    PlayerProfileDialog._build_comparison_panel = _fallback_build_comparison_panel  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_update_comparison_panel'):
    def _fallback_update_comparison_panel(self):  # pragma: no cover - stub
        pass

    PlayerProfileDialog._update_comparison_panel = _fallback_update_comparison_panel  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_prompt_comparison_player'):
    def _fallback_prompt_comparison_player(self):  # pragma: no cover - stub
        return None

    PlayerProfileDialog._prompt_comparison_player = _fallback_prompt_comparison_player  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_load_player_pool'):
    def _fallback_load_player_pool(self):  # pragma: no cover - stub
        return {}

    PlayerProfileDialog._load_player_pool = _fallback_load_player_pool  # type: ignore[attr-defined]

if not hasattr(PlayerProfileDialog, '_attach_player_stats'):
    def _fallback_attach_player_stats(self, player):  # pragma: no cover - stub
        return getattr(player, "season_stats", {})

    PlayerProfileDialog._attach_player_stats = _fallback_attach_player_stats  # type: ignore[attr-defined]


if not hasattr(PlayerProfileDialog, '_collect_stats_history'):
    def _fallback_collect_stats_history(self):  # pragma: no cover - stub
        rows: List[Tuple[str, Dict[str, Any]]] = []
        is_pitcher = getattr(self.player, "is_pitcher", False)
        season = self._stats_to_dict(getattr(self.player, "season_stats", {}), is_pitcher)
        if season:
            try:
                year_label = f"{self._current_season_year():04d}"
            except Exception:
                year_label = "Season"
            rows.append((year_label, season))
        history_entries = getattr(self, "_history_override", []) or []
        for idx, entry in enumerate(history_entries, start=1):
            player_data = entry.get("players", {}).get(self.player.player_id) or {}
            snapshot = player_data.get("stats", player_data)
            data = self._stats_to_dict(snapshot, is_pitcher)
            if data:
                year = entry.get("year")
                label = str(year) if year is not None else f"Year {idx}"
                rows.append((label, data))
        career = self._stats_to_dict(getattr(self.player, "career_stats", {}), is_pitcher)
        if career:
            rows.append(("Career", career))
        return rows

    PlayerProfileDialog._collect_stats_history = _fallback_collect_stats_history  # type: ignore[attr-defined]
