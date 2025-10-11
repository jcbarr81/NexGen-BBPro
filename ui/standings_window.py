from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit

from utils.team_loader import load_teams
from utils.standings_utils import default_record, normalize_record
from utils.path_utils import get_base_dir
from utils.sim_date import get_current_sim_date


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
        raw_standings: dict[str, dict[str, object]] = {}
        if standings_path.exists():
            try:
                with standings_path.open("r", encoding="utf-8") as fh:
                    raw_standings = json.load(fh)
            except (OSError, json.JSONDecodeError):
                raw_standings = {}
        standings: dict[str, dict[str, object]] = {
            team_id: normalize_record(data)
            for team_id, data in raw_standings.items()
        }

        # Build HTML using the same format as the sample standings page.
        sim_date = get_current_sim_date()
        if sim_date:
            try:
                date_obj = datetime.strptime(sim_date, "%Y-%m-%d")
                today = date_obj.strftime("%A, %B %d, %Y")
            except ValueError:
                today = sim_date
        else:
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

        def win_pct(record: dict[str, object]) -> float:
            wins = int(record.get("wins", 0))
            losses = int(record.get("losses", 0))
            games = wins + losses
            return wins / games if games else 0.0

        def fmt_pair(wins: int, losses: int) -> str:
            return f"{wins}-{losses}"

        def fmt_last10(entries: list[str]) -> str:
            wins = sum(1 for r in entries if r == "W")
            losses = sum(1 for r in entries if r == "L")
            return f"{wins}-{losses}"

        def fmt_streak(streak: dict[str, object]) -> str:
            result = streak.get("result")
            length = streak.get("length", 0)
            try:
                length = int(length)
            except (TypeError, ValueError):
                length = 0
            if result in {"W", "L"} and length > 0:
                return f"{result}{length}"
            return "--"

        row_fmt = (
            "{:<22}{:>2}  {:>2}  {:>5}  {:>4}  {:>5}  {:>6}  {:>5}  {:>4}  {:>6}  {:>6}  {:>7}  {:>7}  {:>8}  {:>8}"
        )

        for division in sorted(divisions):
            parts.append(
                f"<b>{row_fmt.format(division, 'W', 'L', 'Pct.', 'GB', '1-run', 'X-inn', 'L-10', 'Strk', 'Home', 'Road', 'v.RHP', 'v.LHP', 'in Div', 'nonDiv')}</b>"
            )

            def sort_key(team_info: tuple[str, str]) -> tuple[float, int]:
                record = standings.get(team_info[1], default_record())
                return (win_pct(record), int(record.get('wins', 0)))

            teams_sorted = sorted(divisions[division], key=sort_key, reverse=True)
            if teams_sorted:
                leader_record = standings.get(teams_sorted[0][1], default_record())
                leader_wins = int(leader_record.get('wins', 0))
                leader_losses = int(leader_record.get('losses', 0))
            else:
                leader_wins = leader_losses = 0

            for name, abbr in teams_sorted:
                record = standings.get(abbr, default_record())
                wins = int(record.get('wins', 0))
                losses = int(record.get('losses', 0))
                games = wins + losses
                pct = wins / games if games else 0.0
                gb_value = ((leader_wins - wins) + (losses - leader_losses)) / 2
                gb_str = '---' if not teams_sorted or abs(gb_value) < 1e-6 else f"{gb_value:.1f}".rstrip('0').rstrip('.')
                if gb_str == '':
                    gb_str = '0'
                one_run = fmt_pair(int(record.get('one_run_wins', 0)), int(record.get('one_run_losses', 0)))
                extra = fmt_pair(int(record.get('extra_innings_wins', 0)), int(record.get('extra_innings_losses', 0)))
                last10 = fmt_last10(list(record.get('last10', [])))
                streak = fmt_streak(record.get('streak', {}))
                home_rec = fmt_pair(int(record.get('home_wins', 0)), int(record.get('home_losses', 0)))
                road_rec = fmt_pair(int(record.get('road_wins', 0)), int(record.get('road_losses', 0)))
                vs_rhp = fmt_pair(int(record.get('vs_rhp_wins', 0)), int(record.get('vs_rhp_losses', 0)))
                vs_lhp = fmt_pair(int(record.get('vs_lhp_wins', 0)), int(record.get('vs_lhp_losses', 0)))
                div_rec = fmt_pair(int(record.get('division_wins', 0)), int(record.get('division_losses', 0)))
                non_div = fmt_pair(int(record.get('non_division_wins', 0)), int(record.get('non_division_losses', 0)))
                parts.append(
                    row_fmt.format(
                        name,
                        wins,
                        losses,
                        f"{pct:.3f}",
                        gb_str,
                        one_run,
                        extra,
                        last10,
                        streak,
                        home_rec,
                        road_rec,
                        vs_rhp,
                        vs_lhp,
                        div_rec,
                        non_div,
                    )
                )
            parts.append("")

        parts.extend(["</pre></body></html>"])
        self.viewer.setHtml("\n".join(parts))
