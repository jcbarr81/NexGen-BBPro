from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
import csv
from pathlib import Path

SCHEDULE_FILE = Path(__file__).resolve().parents[1] / "data" / "schedule.csv"


class ScheduleWindow(QDialog):
    """Dialog displaying the full league schedule."""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Schedule")
        except Exception:  # pragma: no cover - stubs without this method
            pass

        layout = QVBoxLayout(self)

        self.schedule_data: list[dict[str, str]] = []
        if SCHEDULE_FILE.exists():
            with SCHEDULE_FILE.open(newline="") as fh:
                reader = csv.DictReader(fh)
                self.schedule_data = list(reader)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(len(self.schedule_data))
        table.setHorizontalHeaderLabels(["Date", "Away", "Home"])
        for row, game in enumerate(self.schedule_data):
            table.setItem(row, 0, QTableWidgetItem(game.get("date", "")))
            table.setItem(row, 1, QTableWidgetItem(game.get("away", "")))
            table.setItem(row, 2, QTableWidgetItem(game.get("home", "")))
        table.resizeColumnsToContents()

        self.table = table
        layout.addWidget(table)

