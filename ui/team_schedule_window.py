from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
import csv
from pathlib import Path

SCHEDULE_FILE = Path(__file__).resolve().parents[1] / "data" / "schedule.csv"


class TeamScheduleWindow(QDialog):
    """Dialog displaying a team's schedule and results."""

    def __init__(self, team_id: str, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Team Schedule")
        except Exception:  # pragma: no cover
            pass

        layout = QVBoxLayout(self)

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

        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(len(schedule))
        table.setHorizontalHeaderLabels(["Date", "Opponent", "Result"])
        for row, (date, opp, res) in enumerate(schedule):
            table.setItem(row, 0, QTableWidgetItem(date))
            table.setItem(row, 1, QTableWidgetItem(opp))
            table.setItem(row, 2, QTableWidgetItem(res))
        table.resizeColumnsToContents()

        self.table = table
        layout.addWidget(table)
