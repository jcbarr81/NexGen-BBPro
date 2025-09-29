from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel

from .components import Card, section_title, build_metric_row


class AdminHomePage(QWidget):
    """Admin landing page with league overview and quick actions.

    Relies on the parent dashboard to provide metrics and to handle
    navigation/actions. Styling uses shared components and the current theme.
    """

    def __init__(self, dashboard):
        super().__init__()
        self._dashboard = dashboard

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        # Overview metrics ------------------------------------------------
        self.metrics_card = Card()
        self.metrics_card.layout().addWidget(section_title("League Overview"))

        self._metric_values = {
            "Pending Trades": "--",
            "Teams": "--",
            "Players": "--",
            "Season Phase": "--",
        }
        self.metrics_row = build_metric_row(list(self._metric_values.items()), columns=4)
        self.metrics_card.layout().addWidget(self.metrics_row)
        self.metrics_card.layout().addStretch()
        layout.addWidget(self.metrics_card)

        # Key dates/status -----------------------------------------------
        status = Card()
        status.layout().addWidget(section_title("Key Dates"))
        self.next_event_label = QLabel("Draft Day: --")
        self.next_event_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        status.layout().addWidget(self.next_event_label)
        status.layout().addStretch()
        layout.addWidget(status)

        # Shortcuts ------------------------------------------------------
        actions = Card()
        actions.layout().addWidget(section_title("Quick Actions"))
        btn_trades = QPushButton("Review Trades", objectName="Primary")
        btn_trades.clicked.connect(self._dashboard.open_trade_review)
        actions.layout().addWidget(btn_trades)

        btn_progress = QPushButton("Season Progress", objectName="Primary")
        btn_progress.clicked.connect(self._dashboard.open_season_progress)
        actions.layout().addWidget(btn_progress)

        btn_exhibition = QPushButton("Exhibition Game", objectName="Primary")
        btn_exhibition.clicked.connect(self._dashboard.open_exhibition_dialog)
        actions.layout().addWidget(btn_exhibition)

        btn_create = QPushButton("Create League", objectName="Primary")
        btn_create.clicked.connect(self._dashboard.open_create_league)
        actions.layout().addWidget(btn_create)

        actions.layout().addStretch()
        layout.addWidget(actions)

        layout.addStretch()

    def refresh(self) -> None:
        """Refresh metrics and key dates from the dashboard helper."""
        try:
            m = self._dashboard.get_admin_metrics()
        except Exception:
            m = None

        # Update metrics row
        vals = {
            "Pending Trades": (str(m.get("pending_trades")) if m else "--"),
            "Teams": (str(m.get("teams")) if m else "--"),
            "Players": (str(m.get("players")) if m else "--"),
            "Season Phase": (str(m.get("season_phase")) if m else "--"),
        }
        self.metrics_card.layout().removeWidget(self.metrics_row)
        self.metrics_row.setParent(None)
        self.metrics_row = build_metric_row(list(vals.items()), columns=4)
        self.metrics_card.layout().insertWidget(1, self.metrics_row)

        # Update key date/status line
        if m:
            dd = m.get("draft_day") or "--"
            status = m.get("draft_status") or "--"
            self.next_event_label.setText(f"Draft Day: {dd} | Status: {status}")
        else:
            self.next_event_label.setText("Draft Day: --")

