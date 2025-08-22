from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel


class SeasonProgressWindow(QDialog):
    """Placeholder dialog for season progress information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Season Progress")
        except Exception:  # pragma: no cover
            pass

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Season progress details are not available."))
