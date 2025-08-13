from __future__ import annotations

import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit


class StandingsWindow(QDialog):
    """Dialog displaying league standings using an HTML template."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Standings")
        # Expand the dialog so the standings HTML can be viewed without scrolling
        self.setGeometry(100, 100, 1000, 800)

        layout = QVBoxLayout(self)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        # Ensure the text area grows with the dialog
        viewer.setMinimumHeight(760)

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        html_path = os.path.join(base_dir, "samples", "StandingsSample.html")
        try:
            with open(html_path, encoding="utf-8") as f:
                viewer.setHtml(f.read())
        except OSError:
            viewer.setPlainText("Standings data not found.")

        layout.addWidget(viewer)
