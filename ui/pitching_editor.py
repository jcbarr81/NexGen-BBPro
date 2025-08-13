from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout, QGridLayout, QComboBox, QPushButton, QMessageBox
import os
import csv
from utils.pitcher_role import get_role
from utils.pitching_autofill import autofill_pitching_staff

class PitchingEditor(QDialog):
    def __init__(self, team_id):
        super().__init__()
        self.team_id = team_id
        self.setWindowTitle("Pitching Staff Editor")
        self.setMinimumSize(500, 500)

        layout = QVBoxLayout(self)

        self.roles = ["SP1", "SP2", "SP3", "SP4", "SP5", "LR", "MR", "SU", "CL"]
        self.pitcher_dropdowns = {}

        self.players_dict = self.load_players_dict()
        self.act_ids = self.get_act_level_ids()

        grid = QGridLayout()
        for i, role in enumerate(self.roles):
            label = QLabel(role)
            dropdown = QComboBox()
            for pid, pdata in self.players_dict.items():
                if pid in self.act_ids and get_role(pdata):
                    dropdown.addItem(pdata["name"], userData=pid)
            self.pitcher_dropdowns[role] = dropdown
            grid.addWidget(label, i, 0)
            grid.addWidget(dropdown, i, 1)

        layout.addLayout(grid)

        save_btn = QPushButton("Save Pitching Staff")
        save_btn.clicked.connect(self.save_pitching_staff)
        layout.addWidget(save_btn)

        autofill_btn = QPushButton("Auto-Fill Staff")
        autofill_btn.clicked.connect(self.autofill_staff)
        layout.addWidget(autofill_btn)

        clear_btn = QPushButton("Clear Staff")
        clear_btn.clicked.connect(self.clear_staff)
        layout.addWidget(clear_btn)

        self.load_pitching_staff()

    def load_players_dict(self):
        path = os.path.join("data", "players.csv")
        players = {}
        if os.path.exists(path):
            with open(path, newline='', encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    pid = row["player_id"].strip()
                    # Show the pitcher's role (SP/RP) instead of raw "P" when possible
                    role = get_role(row)
                    display_pos = role or row["primary_position"]
                    name = f"{row['first_name']} {row['last_name']} ({display_pos})"
                    players[pid] = {
                        "name": name,
                        "primary_position": row["primary_position"],
                        "role": row.get("role", ""),
                        "endurance": row.get("endurance", ""),
                    }
        return players

    def get_act_level_ids(self):
        act_ids = set()
        path = os.path.join("data", "rosters", f"{self.team_id}.csv")
        if os.path.exists(path):
            with open(path, newline='', encoding="utf-8") as f:
                for row in csv.reader(f):
                    if len(row) >= 2 and row[1].strip().upper() == "ACT":
                        act_ids.add(row[0].strip())
        return act_ids

    def save_pitching_staff(self):
        used_ids = set()
        for role, dropdown in self.pitcher_dropdowns.items():
            player_id = dropdown.currentData()
            if player_id in used_ids:
                QMessageBox.warning(self, "Validation Error", f"{self.players_dict[player_id]['name']} is assigned to multiple roles.")
                return
            if player_id:
                used_ids.add(player_id)
        path = os.path.join("data", "rosters", f"{self.team_id}_pitching.csv")
        with open(path, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            for role, dropdown in self.pitcher_dropdowns.items():
                player_id = dropdown.currentData()
                if player_id:
                    writer.writerow([player_id, role])
        QMessageBox.information(self, "Saved", "Pitching staff saved successfully.")

    def load_pitching_staff(self):
        path = os.path.join("data", "rosters", f"{self.team_id}_pitching.csv")
        if os.path.exists(path):
            with open(path, newline='', encoding="utf-8") as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        player_id, role = row[0], row[1]
                        if role in self.pitcher_dropdowns:
                            dropdown = self.pitcher_dropdowns[role]
                            for i in range(dropdown.count()):
                                if dropdown.itemData(i) == player_id:
                                    dropdown.setCurrentIndex(i)
                                    break

    def autofill_staff(self):
        available = [
            (pid, pdata)
            for pid, pdata in self.players_dict.items()
            if pid in self.act_ids and get_role(pdata)
        ]
        assignments = autofill_pitching_staff(available)
        for role, dropdown in self.pitcher_dropdowns.items():
            pid = assignments.get(role)
            if pid is None:
                dropdown.setCurrentIndex(-1)
                continue
            for i in range(dropdown.count()):
                if dropdown.itemData(i) == pid:
                    dropdown.setCurrentIndex(i)
                    break

    def clear_staff(self):
        for dropdown in self.pitcher_dropdowns.values():
            dropdown.setCurrentIndex(-1)
