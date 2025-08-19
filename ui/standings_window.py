from __future__ import annotations

from collections import defaultdict
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit

from utils.team_loader import load_teams
from utils.path_utils import get_base_dir


class StandingsWindow(QDialog):
    """Dialog displaying league standings from league data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Standings")
        # Expand the dialog so the standings HTML can be viewed without scrolling
        self.setGeometry(100, 100, 1000, 800)

        layout = QVBoxLayout(self)

        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        # Ensure the text area grows with the dialog
        self.viewer.setMinimumHeight(760)

        layout.addWidget(self.viewer)

        self._load_standings()

    def _load_standings(self) -> None:
        """Load league, division and team names into the text viewer."""
        base_dir = get_base_dir()
        league_path = base_dir / "data" / "league.txt"

        try:
            with league_path.open(encoding="utf-8") as f:
                league_name = f.read().strip() or "League"
        except OSError:
            league_name = "League"

        teams = load_teams()
        divisions: dict[str, list[str]] = defaultdict(list)
        for team in teams:
            divisions[team.division].append(f"{team.city} {team.name}")

        parts = [f"<h1>{league_name} Standings</h1>"]
        for division in sorted(divisions):
            parts.append(f"<h2>{division} Division</h2>")
            parts.append("<ul>")
            for name in sorted(divisions[division]):
                parts.append(f"<li>{name}</li>")
            parts.append("</ul>")

        self.viewer.setHtml("\n".join(parts))
