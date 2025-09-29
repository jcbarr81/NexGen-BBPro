from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        # Metrics card ----------------------------------------------------
        self.metrics_card = Card()
        self.metrics_card.layout().addWidget(section_title("Team Snapshot"))
        # Placeholders; populated in refresh()
        self._metric_values = {
            "Record": "--",
            "Run Diff": "--",
            "Next Game": "--",
            "Next Date": "--",
        }
        self.metrics_row = build_metric_row(
            [(k, v) for k, v in self._metric_values.items()], columns=4
        )
        self.metrics_card.layout().addWidget(self.metrics_row)
        self.metrics_card.layout().addStretch()
        layout.addWidget(self.metrics_card)

        # Quick actions card ---------------------------------------------
        actions = Card()
        actions.layout().addWidget(section_title("Quick Actions"))

        btn_lineups = QPushButton("Lineups", objectName="Primary")
        btn_lineups.clicked.connect(self._dashboard.open_lineup_editor)
        actions.layout().addWidget(btn_lineups)

        btn_pitching = QPushButton("Pitching Staff", objectName="Primary")
        btn_pitching.clicked.connect(self._dashboard.open_pitching_editor)
        actions.layout().addWidget(btn_pitching)

        btn_tx = QPushButton("Recent Transactions", objectName="Primary")
        btn_tx.clicked.connect(self._dashboard.open_transactions_page)
        actions.layout().addWidget(btn_tx)

        actions.layout().addStretch()
        layout.addWidget(actions)

        layout.addStretch()

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

