"""Draft tools page migrated from the legacy admin dashboard."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout

from ...components import Card, section_title
from .base import DashboardPage


class DraftPage(DashboardPage):
    """Amateur draft hub with status messaging."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        card = Card()
        card.layout().addWidget(section_title("Amateur Draft"))

        self.draft_status_label = QLabel("")
        self.draft_status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        card.layout().addWidget(self.draft_status_label)

        self.view_draft_pool_button = QPushButton("View Draft Pool")
        self.view_draft_pool_button.setToolTip("Browse the draft pool once Draft Day arrives.")
        card.layout().addWidget(self.view_draft_pool_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.start_resume_draft_button = QPushButton("Start/Resume Draft")
        self.start_resume_draft_button.setToolTip("Open the Draft Console on or after Draft Day.")
        card.layout().addWidget(self.start_resume_draft_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.view_results_button = QPushButton("View Draft Results")
        self.view_results_button.setToolTip("Open results for the current season (after completion).")
        card.layout().addWidget(self.view_results_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.draft_settings_button = QPushButton("Draft Settings")
        self.draft_settings_button.setToolTip("Configure rounds, pool size, and RNG seed (always available).")
        card.layout().addWidget(self.draft_settings_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()


__all__ = ["DraftPage"]
