from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit
import csv
from pathlib import Path

SCHEDULE_FILE = Path(__file__).resolve().parents[1] / "data" / "schedule.csv"


class ScheduleWindow(QDialog):
    """Dialog displaying the full league schedule as HTML."""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Schedule")
            self.setGeometry(100, 100, 800, 600)
        except Exception:  # pragma: no cover - stubs without this method
            pass

        layout = QVBoxLayout(self)

        self.viewer = QTextEdit()
        try:
            self.viewer.setReadOnly(True)
            self.viewer.setMinimumHeight(560)
        except Exception:  # pragma: no cover
            pass
        layout.addWidget(self.viewer)

        schedule_data: list[dict[str, str]] = []
        if SCHEDULE_FILE.exists():
            with SCHEDULE_FILE.open(newline="") as fh:
                reader = csv.DictReader(fh)
                schedule_data = list(reader)

        parts = [
            "<html><head><title>League Schedule</title></head><body>",
            "<b><font size=\"+2\"><center>League Schedule</center></font></b>",
            "<hr><pre><b>Date       Away  Home</b>",
        ]

        for game in schedule_data:
            date = game.get("date", "")
            away = game.get("away", "")
            home = game.get("home", "")
            parts.append(f"{date:<10}{away:<5}{home}")

        parts.extend(["</pre></body></html>"])
        try:
            self.viewer.setHtml("\n".join(parts))
        except Exception:  # pragma: no cover - dummy widgets
            pass

