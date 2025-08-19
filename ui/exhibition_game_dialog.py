from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox,
    QPlainTextEdit,
)
from PyQt6.QtCore import Qt
from typing import Dict

from utils.team_loader import load_teams
from utils.player_loader import load_players_from_csv
from utils.roster_loader import load_roster
from datetime import datetime

from logic.simulation import (
    GameSimulation,
    TeamState,
    generate_boxscore,
    render_boxscore_html,
    save_boxscore_html,
)
from models.pitcher import Pitcher
from logic.playbalance_config import PlayBalanceConfig
from utils.path_utils import get_base_dir


class ExhibitionGameDialog(QDialog):
    """Dialog to select teams and simulate an exhibition game."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simulate Exhibition Game")

        layout = QVBoxLayout()

        self.home_combo = QComboBox()
        self.away_combo = QComboBox()

        data_dir = get_base_dir() / "data"
        teams = load_teams(data_dir / "teams.csv")
        self._teams: Dict[str, str] = {}
        for t in teams:
            label = f"{t.name} ({t.team_id})"
            self.home_combo.addItem(label, userData=t.team_id)
            self.away_combo.addItem(label, userData=t.team_id)
            self._teams[t.team_id] = t.name

        layout.addWidget(QLabel("Home Team:"))
        layout.addWidget(self.home_combo)
        layout.addWidget(QLabel("Away Team:"))
        layout.addWidget(self.away_combo)

        self.simulate_btn = QPushButton("Simulate")
        self.simulate_btn.setEnabled(False)
        layout.addWidget(self.simulate_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.box_score = QPlainTextEdit()
        self.box_score.setReadOnly(True)
        layout.addWidget(self.box_score)

        self.setLayout(layout)

        self.home_combo.currentIndexChanged.connect(self._update_button)
        self.away_combo.currentIndexChanged.connect(self._update_button)
        self.simulate_btn.clicked.connect(self._simulate)
        self._data_dir = data_dir
        self._update_button()

    def _update_button(self) -> None:
        self.simulate_btn.setEnabled(
            self.home_combo.currentData() is not None
            and self.away_combo.currentData() is not None
            and self.home_combo.currentData() != self.away_combo.currentData()
        )

    def _build_state(self, team_id: str) -> TeamState:
        players = {
            p.player_id: p
            for p in load_players_from_csv(self._data_dir / "players.csv")
        }
        roster = load_roster(team_id, self._data_dir / "rosters")

        lineup = []
        bench = []
        pitchers = []
        for pid in roster.act:
            player = players.get(pid)
            if not player:
                continue
            if isinstance(player, Pitcher):
                pitchers.append(player)
            elif len(lineup) < 9:
                lineup.append(player)
            else:
                bench.append(player)

        if len(lineup) < 9:
            raise ValueError(f"Team {team_id} does not have enough position players")
        if not pitchers:
            raise ValueError(f"Team {team_id} does not have any pitchers")

        return TeamState(lineup=lineup, bench=bench, pitchers=pitchers)

    def _simulate(self) -> None:
        home_id = self.home_combo.currentData()
        away_id = self.away_combo.currentData()
        if home_id is None or away_id is None:
            return
        try:
            home_state = self._build_state(home_id)
            away_state = self._build_state(away_id)
            cfg = PlayBalanceConfig.from_file(get_base_dir() / "logic" / "PBINI.txt")
            sim = GameSimulation(home_state, away_state, cfg)
            sim.simulate_game()
            box = generate_boxscore(home_state, away_state)
            text = self._format_box_score(home_id, away_id, box)
            # Render and save an HTML version of the box score
            html = render_boxscore_html(
                box,
                home_name=self._teams.get(home_id, home_id),
                away_name=self._teams.get(away_id, away_id),
            )
            save_boxscore_html("exhibition", html, datetime.now().strftime("%Y%m%d_%H%M%S"))
            if sim.debug_log:
                text += "\n\nStrategy Log:\n" + "\n".join(sim.debug_log)
            positions = sim.defense.set_field_positions()
            if positions:
                text += "\n\nField Positions:\n"
                for sit, pos in positions.items():
                    text += f"{sit}: {pos}\n"
            self.box_score.setPlainText(text)
        except FileNotFoundError as e:
            QMessageBox.warning(self, "Missing Data", str(e))
        except ValueError as e:
            QMessageBox.warning(self, "Missing Data", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to simulate: {e}")

    def _format_box_score(
        self,
        home_id: str,
        away_id: str,
        box: Dict[str, Dict[str, object]],
    ) -> str:
        lines = [
            f"Exhibition Game: {self._teams.get(home_id, home_id)} vs {self._teams.get(away_id, away_id)}",
            "",
            f"Final: {self._teams.get(away_id, away_id)} {box['away']['score']}, {self._teams.get(home_id, home_id)} {box['home']['score']}",
            "",
        ]

        def team_section(label: str, key: str) -> None:
            lines.append(label)
            lines.append("BATTING")
            for entry in box[key]["batting"]:
                p = entry["player"]
                lines.append(
                    f"{p.first_name} {p.last_name}: {entry['h']}-{entry['ab']}, BB {entry['bb']}, SO {entry['so']}, SB {entry['sb']}"
                )
            if box[key]["pitching"]:
                lines.append("PITCHING")
                for entry in box[key]["pitching"]:
                    p = entry["player"]
                    lines.append(
                        f"{p.first_name} {p.last_name}: {entry['pitches']} pitches, BB {entry['bb']}, SO {entry['so']}"
                    )
            lines.append("")

        team_section(f"Away - {self._teams.get(away_id, away_id)}", "away")
        team_section(f"Home - {self._teams.get(home_id, home_id)}", "home")
        return "\n".join(lines)
