"""Utility actions page migrated from the legacy admin dashboard."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QVBoxLayout

from ...components import Card, section_title
from .base import DashboardPage


class UtilitiesPage(DashboardPage):
    """Miscellaneous utilities for data management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = Card()
        card.layout().addWidget(section_title("Utilities"))

        self.generate_logos_button = QPushButton("Generate Team Logos")
        card.layout().addWidget(self.generate_logos_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.generate_avatars_button = QPushButton("Generate Player Avatars")
        card.layout().addWidget(self.generate_avatars_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        card.layout().addStretch()
        layout.addWidget(card)
        layout.addStretch()


__all__ = ["UtilitiesPage"]
