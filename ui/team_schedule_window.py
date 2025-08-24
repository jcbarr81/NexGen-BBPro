from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit
import csv
from pathlib import Path

SCHEDULE_FILE = Path(__file__).resolve().parents[1] / "data" / "schedule.csv"


class TeamScheduleWindow(QDialog):
    """Dialog displaying a team's schedule and results as HTML."""

    def __init__(self, team_id: str, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Team Schedule")
            self.setGeometry(100, 100, 800, 600)
        except Exception:  # pragma: no cover
            pass

        layout = QVBoxLayout(self)

        self.viewer = QTextEdit()
        try:
            self.viewer.setReadOnly(True)
            self.viewer.setMinimumHeight(560)
        except Exception:  # pragma: no cover
            pass
        layout.addWidget(self.viewer)

        schedule: list[tuple[str, str, str]] = []
        if SCHEDULE_FILE.exists():
            with SCHEDULE_FILE.open(newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if row.get("home") == team_id or row.get("away") == team_id:
                        opponent = (
                            row.get("away") if row.get("home") == team_id else row.get("home")
                        )
                        venue = "vs" if row.get("home") == team_id else "at"
                        result = row.get("result", "")
                        schedule.append((row.get("date", ""), f"{venue} {opponent}", result))

        parts = [
            "<html><head><title>Team Schedule</title></head><body>",
            f"<b><font size=\"+2\"><center>{team_id} Schedule</center></font></b>",
            "<hr><pre><b>Date       Opponent  Result</b>",
        ]

        for date, opp, res in schedule:
            parts.append(f"{date:<10}{opp:<10}{res}")

        parts.extend(["</pre></body></html>"])
        try:
            self.viewer.setHtml("\n".join(parts))
        except Exception:  # pragma: no cover
            pass
