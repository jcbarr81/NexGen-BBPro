"""Placeholder dialog for future transaction features."""

from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout


class TransactionsWindow(QDialog):
    """Simple dialog announcing upcoming transaction tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transactions")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Coming soon"))
        self.setLayout(layout)

