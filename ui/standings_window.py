from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class StandingsWindow(QDialog):
    """Simple dialog displaying dummy league standings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Standings")

        layout = QVBoxLayout(self)

        table = QTableWidget()
        data = [
            ("Team A", 10, 5),
            ("Team B", 8, 7),
            ("Team C", 7, 8),
            ("Team D", 5, 10),
        ]
        table.setColumnCount(3)
        table.setRowCount(len(data))
        table.setHorizontalHeaderLabels(["Team", "Wins", "Losses"])
        for row, (team, wins, losses) in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(team))
            table.setItem(row, 1, QTableWidgetItem(str(wins)))
            table.setItem(row, 2, QTableWidgetItem(str(losses)))
        table.resizeColumnsToContents()
        layout.addWidget(table)
