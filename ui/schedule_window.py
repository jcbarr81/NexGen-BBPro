from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class ScheduleWindow(QDialog):
    """Dialog displaying a simple placeholder schedule."""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            # Set a descriptive window title if supported by the widget backend
            self.setWindowTitle("Schedule")
        except Exception:  # pragma: no cover - stubs without this method
            pass

        layout = QVBoxLayout(self)

        # Default schedule data used for placeholder view
        self.schedule_data = [
            ("2024-04-01", "Team A vs Team B"),
            ("2024-04-02", "Team C vs Team D"),
            ("2024-04-03", "Team A at Team C"),
        ]

        table = QTableWidget()
        table.setColumnCount(2)
        table.setRowCount(len(self.schedule_data))
        table.setHorizontalHeaderLabels(["Date", "Game"])
        for row, (date, game) in enumerate(self.schedule_data):
            table.setItem(row, 0, QTableWidgetItem(date))
            table.setItem(row, 1, QTableWidgetItem(game))
        table.resizeColumnsToContents()

        # Expose table for tests
        self.table = table
        layout.addWidget(table)

