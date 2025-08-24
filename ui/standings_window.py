from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json

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
        divisions: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for team in teams:
            divisions[team.division].append((f"{team.city} {team.name}", team.abbreviation))

        standings_path = base_dir / "data" / "standings.json"
        standings: dict[str, dict[str, int]] = {}
        if standings_path.exists():
            try:
                with standings_path.open("r", encoding="utf-8") as fh:
                    standings = json.load(fh)
            except (OSError, json.JSONDecodeError):
                standings = {}

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

        def win_pct(team_abbr: str) -> float:
            rec = standings.get(team_abbr, {})
            wins = int(rec.get("wins", 0))
            losses = int(rec.get("losses", 0))
            games = wins + losses
            return wins / games if games else 0.0

        for division in sorted(divisions):
            parts.append(f"<b>{header.format(division)}</b>")
            teams = sorted(
                divisions[division],
                key=lambda t: win_pct(t[1]),
                reverse=True,
            )
            for name, abbr in teams:
                record = standings.get(abbr, {})
                wins = int(record.get("wins", 0))
                losses = int(record.get("losses", 0))
                games = wins + losses
                pct = wins / games if games else 0.0
                parts.append(
                    f"{name:<22}{wins:>2}  {losses:>2}  {pct:.3f}   ---     0-0    0-0    0-0   W  0     "
                    "0-0    0-0      0-0    0-0      0-0    0-0"
                )
            parts.append("")

        parts.extend(["</pre></body></html>"])
        self.viewer.setHtml("\n".join(parts))
