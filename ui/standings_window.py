from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit

from utils.team_loader import load_teams


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
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        league_path = os.path.join(base_dir, "data", "league.txt")

        try:
            with open(league_path, encoding="utf-8") as f:
                league_name = f.read().strip() or "League"
        except OSError:
            league_name = "League"

        teams = load_teams()
        divisions: dict[str, list[str]] = defaultdict(list)
        for team in teams:
            divisions[team.division].append(f"{team.city} {team.name}")

        # Build HTML using the same format as the sample standings page.
        today = datetime.now().strftime("%A, %B %d, %Y")
        parts = [
            "<html><head>",
            f"<title>{league_name} Standings</title>",
            "</head><body>",
            "<b><font size=\"+2\"><center>",
            f"{league_name} Standings",
            "</center></font>",
            "<font size=\"+1\"><center>",
            today,
            "</center></font></b>",
            "<hr><b><font size=\"+1\"><center>",
            league_name,
            "</center></font></b>",
            "<pre>",
        ]

        header = (
            "{:<22}W   L   Pct.    GB    1-run  X-inn   L-10  Strk     Home   "
            "Road    v.RHP  v.LHP   in Div  nonDiv"
        )

        for division in sorted(divisions):
            parts.append(f"<b>{header.format(division)}</b>")
            for name in sorted(divisions[division]):
                parts.append(
                    f"{name:<22}0   0   .000   ---     0-0    0-0    0-0   W  0     "
                    "0-0    0-0      0-0    0-0      0-0    0-0"
                )
            parts.append("")

        parts.extend(["</pre></body></html>"])
        self.viewer.setHtml("\n".join(parts))
