from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from types import SimpleNamespace

try:
    from PyQt6.QtCore import QPointF, Qt
except ImportError:  # pragma: no cover - test stubs
    Qt = SimpleNamespace(
        AlignmentFlag=SimpleNamespace(
            AlignCenter=None,
            AlignHCenter=None,
            AlignVCenter=None,
            AlignLeft=None,
            AlignRight=None,
            AlignTop=None,
            AlignBottom=None,
        ),
        ToolButtonStyle=SimpleNamespace(ToolButtonTextBesideIcon=None),
    )

    class QPointF:  # type: ignore[too-many-ancestors]
        def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
            self._x = x
            self._y = y

        def x(self) -> float:
            return self._x

        def y(self) -> float:
            return self._y

try:
    from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
except ImportError:  # pragma: no cover - test stubs
    class _GraphicDummy:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __getattr__(self, name):
            def _noop(*_args, **_kwargs):
                return None

            return _noop

    QColor = QFont = QPainter = QPen = QPolygonF = _GraphicDummy
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .components import Card, section_title, build_metric_row


class OwnerHomePage(QWidget):
    """Landing page for the Owner Dashboard with quick metrics and actions.

    This page relies on the dashboard to provide metric data and to open
    dialogs for common actions. It keeps styling consistent using the
    shared Card and section title components and the current theme.
    """

    def __init__(self, dashboard):
        super().__init__()
        self._dashboard = dashboard
        self._layout_mode: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(24)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._content = QWidget()
        self._content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._content.setMaximumWidth(1320)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(24)

        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(24)
        self._grid.setVerticalSpacing(24)
        content_layout.addLayout(self._grid)
        root.addWidget(self._content, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Metrics card ----------------------------------------------------
        self.metrics_card = Card()
        self.metrics_card.setMinimumHeight(180)
        self.metrics_card.layout().addWidget(section_title("Team Snapshot"))
        self._metric_values = {
            "Record": "--",
            "Run Diff": "--",
            "Next Game": "--",
            "Next Date": "--",
            "Streak": "--",
            "Last 10": "--",
            "Injuries": "0",
            "Prob SP": "--",
        }
        self.metrics_row = build_metric_row(
            [(k, v) for k, v in self._metric_values.items()], columns=4
        )
        self.metrics_card.layout().addWidget(self.metrics_row)

        # Readiness & matchup card ---------------------------------
        self.readiness_card = Card()
        self.readiness_card.setMinimumHeight(180)
        self.readiness_card.layout().addWidget(section_title("Readiness & Matchup"))
        readiness_row = QHBoxLayout()
        readiness_row.setSpacing(16)
        self.bullpen_widget = BullpenReadinessWidget()
        self.matchup_widget = MatchupScoutWidget()
        self.bullpen_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.matchup_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        readiness_row.addWidget(self.bullpen_widget, 1)
        readiness_row.addWidget(self.matchup_widget, 1)
        self.readiness_card.layout().addLayout(readiness_row)

        # Quick actions card ---------------------------------------------
        self.quick_actions_card = Card()
        self.quick_actions_card.setMinimumHeight(180)
        self.quick_actions_card.layout().addWidget(section_title("Quick Actions"))
        self.quick_grid = QGridLayout()
        self.quick_grid.setContentsMargins(6, 12, 6, 12)
        self.quick_grid.setHorizontalSpacing(24)
        self.quick_grid.setVerticalSpacing(18)
        self.quick_buttons: list[QPushButton] = []
        button_data = [
            ("Lineups", self._dashboard.open_lineup_editor),
            ("Pitching Staff", self._dashboard.open_pitching_editor),
            ("Recent Transactions", self._dashboard.open_transactions_page),
            ("Team Settings", self._dashboard.open_team_settings_dialog),
            ("Reassign Players", self._dashboard.open_reassign_players_dialog),
            ("Team Stats", lambda: self._dashboard.open_team_stats_window("team")),
            ("League Standings", self._dashboard.open_standings_window),
            ("Full Roster", self._dashboard.open_player_browser_dialog),
        ]
        for idx, (label, callback) in enumerate(button_data):
            btn = self._make_action_button(label, callback)
            row, col = divmod(idx, 2)
            self.quick_grid.addWidget(btn, row, col)
            self.quick_buttons.append(btn)
        self.quick_actions_card.layout().addLayout(self.quick_grid)

        # Trendlines card -----------------------------------------------
        self.trend_card = Card()
        self.trend_card.setMinimumHeight(280)
        self.trend_card.layout().addWidget(section_title("Trendlines (Last 10 Games)"))
        self.trend_chart = TrendChartWidget()
        self.trend_chart.setMinimumHeight(240)
        self.trend_chart.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.trend_card.layout().addWidget(self.trend_chart)

        # Recent News card ----------------------------------------------
        self.news_card = Card()
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_row.addWidget(section_title("Recent News"))
        header_row.addStretch()
        self.news_toggle = QToolButton()
        self.news_toggle.setText("View all")
        self.news_toggle.setCheckable(True)
        self.news_toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        self.news_toggle.clicked.connect(self._toggle_news)
        header_row.addWidget(self.news_toggle)
        self.news_card.layout().addLayout(header_row)

        self.news_preview = QLabel("No recent items.")
        self.news_preview.setWordWrap(True)
        self.news_preview.setObjectName("NewsPreview")
        self.news_card.layout().addWidget(self.news_preview)

        self.news_full = QLabel("No recent items.")
        self.news_full.setWordWrap(True)
        self.news_full.setObjectName("NewsFull")
        self.news_full.setVisible(False)
        self.news_card.layout().addWidget(self.news_full)

        self._news_lines: list[str] = []

        self._cards = [
            self.metrics_card,
            self.readiness_card,
            self.quick_actions_card,
            self.trend_card,
            self.news_card,
        ]
        self._layout_mode = None
        self._apply_layout_mode("wide")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Refresh metrics from the dashboard helpers."""
        try:
            m = self._dashboard.get_quick_metrics()
        except Exception:
            m = None

        # Update our metric values
        new_values = {
            "Record": m.get("record", "--") if m else "--",
            "Run Diff": m.get("run_diff", "--") if m else "--",
            "Next Game": m.get("next_opponent", "--") if m else "--",
            "Next Date": m.get("next_date", "--") if m else "--",
            "Streak": m.get("streak", "--") if m else "--",
            "Last 10": m.get("last10", "--") if m else "--",
            "Injuries": str(m.get("injuries", 0) if m else 0),
            "Prob SP": m.get("prob_sp", "--") if m else "--",
        }

        # Rebuild metric row content in-place
        # Remove existing metric row widget and replace
        self.metrics_card.layout().removeWidget(self.metrics_row)
        self.metrics_row.setParent(None)
        self._metric_values = new_values
        self.metrics_row = build_metric_row(
            [(k, v) for k, v in self._metric_values.items()], columns=4
        )
        self.metrics_card.layout().insertWidget(1, self.metrics_row)

        bullpen_data = m.get("bullpen", {}) if m else {}
        self.bullpen_widget.update_data(bullpen_data)
        matchup_data = m.get("matchup", {}) if m else {}
        self.matchup_widget.update_matchup(matchup_data)
        trend_data = m.get("trends", {}) if m else {}
        self.trend_chart.update_trends(trend_data)

        # Update recent news
        try:
            from utils.news_logger import NEWS_FILE
            from pathlib import Path

            p = Path(NEWS_FILE)
            if p.exists():
                lines = [
                    line
                    for line in p.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                # Keep a reasonable window of recent items, newest at the end
                self._news_lines = lines[-40:]
            else:
                self._news_lines = []
        except Exception:
            self._news_lines = []

        self._update_news_display()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_layout_mode()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._update_layout_mode()

    def _make_action_button(self, label: str, callback: Callable[[], None]) -> QPushButton:
        btn = QPushButton(label, objectName="Primary")
        btn.setMinimumHeight(64)
        btn.setMinimumWidth(150)
        btn.setMaximumWidth(200)
        btn.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        btn.clicked.connect(callback)
        return btn

    def _toggle_news(self, checked: bool) -> None:
        if not self.news_toggle.isEnabled():
            self.news_toggle.setChecked(False)
            return
        self.news_full.setVisible(checked)
        self.news_toggle.setText("Hide full feed" if checked else "View all")

    def _update_news_display(self) -> None:
        if not self._news_lines:
            self.news_preview.setText("No recent items.")
            self.news_full.setText("No recent items.")
            self.news_toggle.setEnabled(False)
            self.news_toggle.setChecked(False)
            self.news_toggle.setText("View all")
            self.news_full.setVisible(False)
            return

        preview_lines = list(reversed(self._news_lines[-3:]))
        self.news_preview.setText("\n".join(preview_lines))
        self.news_full.setText("\n".join(reversed(self._news_lines)))

        has_extra = len(self._news_lines) > 3
        self.news_toggle.setEnabled(has_extra)
        if not has_extra:
            self.news_toggle.setChecked(False)
            self.news_toggle.setText("View all")
            self.news_full.setVisible(False)
        else:
            self.news_full.setVisible(self.news_toggle.isChecked())
            self.news_toggle.setText(
                "Hide full feed" if self.news_toggle.isChecked() else "View all"
            )

    def _arrange_quick_actions(self, columns: int) -> None:
        for idx in range(self.quick_grid.count() - 1, -1, -1):
            item = self.quick_grid.takeAt(idx)
            if item and item.widget():
                item.widget().setParent(None)

        narrow = columns == 1
        for btn in self.quick_buttons:
            if narrow:
                btn.setMinimumWidth(0)
                btn.setMaximumWidth(16777215)
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
            else:
                btn.setMinimumWidth(150)
                btn.setMaximumWidth(200)
                btn.setSizePolicy(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Expanding,
                )
        for idx, btn in enumerate(self.quick_buttons):
            row, col = divmod(idx, columns)
            self.quick_grid.addWidget(btn, row, col)
            self.quick_grid.setAlignment(btn, Qt.AlignmentFlag.AlignHCenter)

        for idx in range(columns):
            stretch = 1 if narrow else 0
            self.quick_grid.setColumnStretch(idx, stretch)
            if not narrow:
                self.quick_grid.setColumnMinimumWidth(idx, 160)

    def _apply_layout_mode(self, mode: str) -> None:
        if self._layout_mode == mode:
            return
        self._layout_mode = mode
        for card in self._cards:
            self._grid.removeWidget(card)

        if mode == "wide":
            self._arrange_quick_actions(columns=2)
            self._place_card(self.metrics_card, 0, 0)
            self._place_card(self.quick_actions_card, 0, 1)
            self._place_card(self.readiness_card, 1, 0)
            self._place_card(self.news_card, 1, 1)
            self._place_card(self.trend_card, 2, 0, 1, 2)
            self._grid.setColumnStretch(0, 3)
            self._grid.setColumnStretch(1, 2)
            self._grid.setColumnStretch(2, 0)
            self._grid.setRowStretch(0, 0)
            self._grid.setRowStretch(1, 0)
            self._grid.setRowStretch(2, 1)
        elif mode == "medium":
            self._arrange_quick_actions(columns=2)
            self._place_card(self.metrics_card, 0, 0)
            self._place_card(self.quick_actions_card, 0, 1)
            self._place_card(self.readiness_card, 1, 0)
            self._place_card(self.news_card, 1, 1)
            self._place_card(self.trend_card, 2, 0, 1, 2)
            self._grid.setColumnStretch(0, 1)
            self._grid.setColumnStretch(1, 1)
            self._grid.setColumnStretch(2, 0)
            self._grid.setRowStretch(0, 0)
            self._grid.setRowStretch(1, 0)
            self._grid.setRowStretch(2, 1)
        else:
            self._arrange_quick_actions(columns=1)
            for row, card in enumerate(self._cards):
                self._place_card(card, row, 0)
            self._grid.setColumnStretch(0, 1)
            self._grid.setColumnStretch(1, 0)
            self._grid.setColumnStretch(2, 0)
            for idx in range(len(self._cards)):
                self._grid.setRowStretch(idx, 0)
            self._grid.setRowStretch(len(self._cards) - 1, 1)

    def _update_layout_mode(self) -> None:
        # Force the wide layout for now so the dashboard always shows two columns.
        self._apply_layout_mode("wide")

    def _place_card(
        self,
        card: QWidget,
        row: int,
        column: int,
        row_span: int = 1,
        column_span: int = 1,
    ) -> None:
        """Insert a card into the grid with consistent alignment."""

        self._grid.addWidget(card, row, column, row_span, column_span)
        self._grid.setAlignment(card, Qt.AlignmentFlag.AlignTop)


class BullpenReadinessWidget(QWidget):
    """Compact summary of bullpen availability."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.summary_label = QLabel("Bullpen metrics unavailable.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-weight:600;")
        layout.addWidget(self.summary_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._badges: Dict[str, QLabel] = {}
        palette = {
            "ready": ("Ready", QColor(47, 158, 68)),
            "limited": ("Limited", QColor(245, 159, 0)),
            "rest": ("Rest", QColor(224, 49, 49)),
        }
        for key, (label, color) in palette.items():
            badge = QLabel(f"{label}: 0")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                "border-radius: 6px; padding: 4px 8px; "
                f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, 36); "
                f"color: rgb({color.red()}, {color.green()}, {color.blue()}); font-weight: 600;"
            )
            badge.setMinimumWidth(72)
            row.addWidget(badge)
            self._badges[key] = badge
        layout.addLayout(row)
        self._detail: List[Dict[str, Any]] = []

    def update_data(self, data: Dict[str, Any] | None) -> None:
        if not data:
            self.summary_label.setText("Bullpen metrics unavailable.")
            for key, badge in self._badges.items():
                label = "Ready" if key == "ready" else key.capitalize()
                badge.setText(f"{label}: 0")
            self.setToolTip("Bullpen readiness details unavailable.")
            return

        summary = data.get("headline") or "Bullpen outlook pending."
        self.summary_label.setText(summary)
        for key, badge in self._badges.items():
            label = "Ready" if key == "ready" else key.capitalize()
            value = int(data.get(key, 0) or 0)
            badge.setText(f"{label}: {value}")

        detail_lines: List[str] = []
        for item in data.get("detail", []) or []:
            name = item.get("name") or item.get("player_id") or "Unknown"
            status = item.get("status", "--")
            last_pitches = item.get("last_pitches", 0)
            last_used = item.get("last_used") or "--"
            detail_lines.append(
                f"{name}: {status} (last used {last_used}, {last_pitches} pitches)"
            )
        if detail_lines:
            self.setToolTip("\n".join(detail_lines))
        else:
            self.setToolTip("No bullpen usage recorded yet.")


class MatchupScoutWidget(QWidget):
    """Upcoming opponent snapshot."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QLabel("No upcoming opponent detected.")
        self.header.setStyleSheet("font-weight:600;")
        layout.addWidget(self.header)

        self.subheader = QLabel("--")
        self.subheader.setStyleSheet("color: #495057;")
        layout.addWidget(self.subheader)

        self.detail = QLabel("--")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)

    def update_matchup(self, data: Dict[str, Any] | None) -> None:
        if not data:
            self.header.setText("No upcoming opponent detected.")
            self.subheader.setText("--")
            self.detail.setText("Schedule context unavailable.")
            return

        opponent = data.get("opponent", "--")
        date_token = data.get("date", "--")
        venue = data.get("venue", "--")
        self.header.setText(f"{opponent} | {date_token} | {venue}")

        record = data.get("record", "--")
        run_diff = data.get("run_diff", "--")
        streak = data.get("streak", "--")
        self.subheader.setText(f"Record {record} | RD {run_diff} | Streak {streak}")

        note = data.get("note", "Opponent analytics unavailable.")
        team_prob = data.get("team_probable", "--")
        opp_prob = data.get("opponent_probable", "--")
        self.detail.setText(f"{note}\nProbable: {team_prob} vs {opp_prob}")


class TrendChartWidget(QWidget):
    """Lightweight dual-line chart for recent trends."""

    def __init__(self) -> None:
        super().__init__()
        self._dates: List[str] = []
        self._series: Dict[str, List[float]] = {}
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def update_trends(self, data: Dict[str, Any] | None) -> None:
        if not data:
            self._dates = []
            self._series = {}
            self.update()
            return
        self._dates = list(data.get("dates", []))
        series = data.get("series", {}) or {}
        self._series = {
            "runs_per_game": list(series.get("runs_per_game", [])),
            "runs_allowed_per_game": list(series.get("runs_allowed_per_game", [])),
            "win_pct": list(series.get("win_pct", [])),
        }
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(16, 16, -16, -32)
        scored = self._series.get("runs_per_game") or []
        allowed = self._series.get("runs_allowed_per_game") or []
        if not scored or not allowed or len(scored) != len(allowed):
            painter.setPen(QPen(Qt.GlobalColor.gray))
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                "Trend data unavailable.",
            )
            return

        points = len(scored)
        if points == 1:
            scored = scored * 2
            allowed = allowed * 2
            self._dates = (self._dates or ["--"]) * 2
            points = 2

        min_val = min(min(scored), min(allowed))
        max_val = max(max(scored), max(allowed))
        if abs(max_val - min_val) < 0.25:
            max_val += 0.5
            min_val -= 0.5

        def _map(value: float) -> float:
            if max_val == min_val:
                return rect.bottom()
            ratio = (value - min_val) / (max_val - min_val)
            return rect.bottom() - ratio * rect.height()

        x_step = rect.width() / max(1, points - 1)
        scored_poly = QPolygonF(
            QPointF(rect.left() + idx * x_step, _map(val))
            for idx, val in enumerate(scored)
        )
        allowed_poly = QPolygonF(
            QPointF(rect.left() + idx * x_step, _map(val))
            for idx, val in enumerate(allowed)
        )

        axis_pen = QPen(QColor("#adb5bd"))
        painter.setPen(axis_pen)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.bottomLeft(), rect.topLeft())

        painter.setPen(QPen(QColor(47, 158, 68), 2))
        painter.drawPolyline(scored_poly)
        painter.setPen(QPen(QColor(224, 49, 49), 2))
        painter.drawPolyline(allowed_poly)

        painter.setPen(QPen(QColor("#212529")))
        painter.setFont(QFont(painter.font().family(), 9, QFont.Weight.Medium))
        legend_y = rect.top() - 6
        painter.drawText(rect.left(), legend_y, "Runs For")
        painter.drawText(rect.left() + 90, legend_y, "Runs Allowed")

        painter.setPen(QPen(QColor("#495057")))
        if self._dates:
            painter.drawText(
                rect.left(),
                rect.bottom() + 16,
                self._dates[0],
            )
            painter.drawText(
                rect.right() - 60,
                rect.bottom() + 16,
                self._dates[-1],
            )

        win_series = self._series.get("win_pct") or []
        if win_series:
            current = win_series[-1]
            painter.drawText(
                rect.right() - 130,
                rect.top() - 6,
                f"Win% trend: {current:.3f}",
            )

        painter.end()
