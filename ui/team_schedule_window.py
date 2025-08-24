from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
import csv
from pathlib import Path

from .boxscore_window import BoxScoreWindow

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

        self.viewer = QTableWidget(0, 3)
        try:
            self.viewer.setHorizontalHeaderLabels(["Date", "Opponent", "Result"])
            self.viewer.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.viewer.setMinimumHeight(560)
            self.viewer.cellDoubleClicked.connect(self._open_boxscore)
        except Exception:  # pragma: no cover
            pass
        layout.addWidget(self.viewer)

        self._schedule: list[dict[str, str]] = []
        if SCHEDULE_FILE.exists():
            with SCHEDULE_FILE.open(newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if row.get("home") == team_id or row.get("away") == team_id:
                        opponent = row.get("away") if row.get("home") == team_id else row.get("home")
                        venue = "vs" if row.get("home") == team_id else "at"
                        entry = {
                            "date": row.get("date", ""),
                            "opponent": f"{venue} {opponent}",
                            "result": row.get("result", ""),
                            "boxscore": row.get("boxscore", ""),
                        }
                        self._schedule.append(entry)

        try:
            self.viewer.setRowCount(len(self._schedule))
            for r, game in enumerate(self._schedule):
                for c, key in enumerate(["date", "opponent", "result"]):
                    item = QTableWidgetItem(game.get(key, ""))
                    self.viewer.setItem(r, c, item)
        except Exception:  # pragma: no cover
            pass

    def _open_boxscore(self, row: int, column: int) -> None:
        if column != 2:
            return
        game = self._schedule[row]
        path = game.get("boxscore")
        if path:
            dlg = BoxScoreWindow(path, self)
            try:
                dlg.exec()
            except Exception:  # pragma: no cover
                pass
