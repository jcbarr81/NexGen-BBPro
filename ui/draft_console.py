from __future__ import annotations

"""Minimal Draft Console (scaffold).

This dialog pauses the season on Draft Day, generates a draft pool for the
current year if needed, and allows the commissioner to proceed. It is a
placeholder to validate pause/resume flow and persistence.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from utils.path_utils import get_base_dir
from playbalance.draft_pool import generate_draft_pool, save_draft_pool, load_draft_pool


class DraftConsole(QDialog):
    def __init__(self, draft_date: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Amateur Draft — Commissioner's Console")
        self.resize(640, 360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        year = int(draft_date.split("-")[0]) if draft_date else 0
        self.year = year
        layout.addWidget(QLabel(f"Draft Day: {draft_date}"))
        self.status = QLabel("Draft pool not generated yet.")
        layout.addWidget(self.status)

        btn_gen = QPushButton("Generate Draft Pool")
        btn_start = QPushButton("Complete Draft (Auto)")
        btn_close = QPushButton("Close")
        btn_gen.setObjectName("Primary")
        btn_start.setObjectName("Primary")
        layout.addWidget(btn_gen)
        layout.addWidget(btn_start)
        layout.addStretch(1)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        btn_gen.clicked.connect(self._generate_pool)
        btn_start.clicked.connect(self._auto_complete)
        btn_close.clicked.connect(self.accept)

        # Show existing pool status
        existing = load_draft_pool(self.year)
        if existing:
            self.status.setText(f"Draft pool loaded ({len(existing)} players).")

    def _generate_pool(self) -> None:
        pool = generate_draft_pool(self.year, size=200)
        save_draft_pool(self.year, pool)
        self.status.setText(f"Draft pool generated ({len(pool)} players).")

    def _auto_complete(self) -> None:
        # Placeholder: in phase 1 we just confirm and close.
        QMessageBox.information(self, "Draft Complete", "Auto-draft placeholder complete.")
        self.accept()


__all__ = ["DraftConsole"]

