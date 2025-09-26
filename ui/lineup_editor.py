from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QComboBox,
    QPushButton,
    QWidget,
    QMessageBox,
    QGroupBox,
    QListWidget,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QPropertyAnimation
import csv
from pathlib import Path

from utils.pitcher_role import get_role
from utils.path_utils import get_base_dir

class LineupEditor(QDialog):
    def __init__(self, team_id):
        self.team_id = team_id
        super().__init__()
        self.setWindowTitle("Lineup Editor")
        self.setMinimumSize(900, 600)

        layout = QHBoxLayout()
        self.setLayout(layout)

        # Left: Field diagram
        field_container = QWidget()
        field_layout = QVBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(0)

        self.field_label = QLabel()
        field_path = get_base_dir() / "assets" / "field_diagram.png"
        if field_path.exists():
            pixmap = QPixmap(str(field_path)).scaledToWidth(
                400, Qt.TransformationMode.SmoothTransformation
            )
            self.field_label.setPixmap(pixmap)
            overlay_w, overlay_h = pixmap.width(), pixmap.height()
        else:
            self.field_label.setText("Field Image Placeholder")
            self.field_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            overlay_w, overlay_h = 400, 500
        self.field_label.setFixedSize(overlay_w, overlay_h)
        field_layout.addWidget(self.field_label)

        self.field_overlay = QWidget(self.field_label)
        self.field_overlay.setGeometry(0, 0, overlay_w, overlay_h)
        self.field_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self.field_overlay.setStyleSheet("background: transparent;")

        self.position_labels = {}
        y_offset = 0
        position_coords = {
            "C": (160, 303),
            "1B": (225, 163),
            "2B": (220, 111),
            "SS": (98, 111),
            "3B": (62, 162),
            "LF": (55, 57),
            "CF": (158, 22),
            "RF": (230, 57),
            "DH": (275, 237),
        }
        for pos, (x, y) in position_coords.items():
            label = QLabel("", self.field_overlay)
            label.move(x, y + y_offset)
            label.setStyleSheet(
                "color: blue; font-size: 9px; font-weight: bold; background-color: rgba(255, 255, 255, 0.6); border-radius: 4px;"
            )
            label.setFixedWidth(100)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            self.position_labels[pos] = label

        layout.addWidget(field_container)

        # Right: Batting order and bench
        right_container = QWidget()
        right_panel = QVBoxLayout(right_container)
        right_panel.setContentsMargins(10, 10, 10, 10)
        right_panel.setSpacing(12)

        # View selector for vs LHP / vs RHP
        view_selector_group = QGroupBox("Lineup View Mode")
        view_selector_layout = QHBoxLayout()
        self.view_selector = QComboBox()
        self.view_selector.addItems(["vs LHP", "vs RHP"])
        view_selector_layout.addWidget(QLabel("View Lineup For:"))
        view_selector_layout.addWidget(self.view_selector)
        view_selector_group.setLayout(view_selector_layout)
        right_panel.addWidget(view_selector_group)

        # Batting Order
        order_label = QLabel("Batting Order")
        order_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_panel.addWidget(order_label)

        self.order_grid = QGridLayout()
        self.player_dropdowns = []
        self.position_dropdowns = []

        self.players_dict = self.load_players_dict()
        self.act_level_ids = self.get_act_level_ids()
        self.act_players = [
            (pid, pdata["name"]) for pid, pdata in self.players_dict.items()
            if not pdata.get("is_pitcher") and pid in self.act_level_ids
        ]

        for i in range(9):
            spot = QLabel(str(i + 1))
            player_dropdown = QComboBox()
            pos_dropdown = QComboBox()
            pos_dropdown.addItems(["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"])
            pos_dropdown.currentIndexChanged.connect(lambda _, i=i: (self.update_player_dropdown(i), self.update_overlay_label(i), self.update_bench_display()))

            self.order_grid.addWidget(spot, i, 0)
            self.order_grid.addWidget(player_dropdown, i, 1)
            self.order_grid.addWidget(pos_dropdown, i, 2)

            player_dropdown.currentIndexChanged.connect(lambda _, i=i: (self.update_overlay_label(i), self.update_bench_display()))

            self.player_dropdowns.append(player_dropdown)
            self.position_dropdowns.append(pos_dropdown)

        right_panel.addLayout(self.order_grid)

        bench_label = QLabel("Substitute / Bench")
        bench_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        right_panel.addWidget(bench_label)

        self.bench_display = QListWidget()
        self.bench_display.setMinimumHeight(100)
        self.bench_display.setMaximumHeight(150)
        self.bench_display.setStyleSheet("margin-bottom: 10px;")
        self.bench_display.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        right_panel.addWidget(self.bench_display)

        save_button = QPushButton("Save Lineup")
        save_button.clicked.connect(self.save_lineup)
        right_panel.addWidget(save_button)

        autofill_button = QPushButton("Auto-Fill Lineup")
        autofill_button.clicked.connect(self.autofill_lineup)
        right_panel.addWidget(autofill_button)

        clear_button = QPushButton("Clear Lineup")
        clear_button.clicked.connect(self.clear_lineup)
        right_panel.addWidget(clear_button)

        layout.addWidget(right_container)

        self.view_selector.currentIndexChanged.connect(self.switch_view)
        self.current_view = "vs LHP"
        self.load_lineup()
        self.update_bench_display()

    def autofill_lineup(self):
        positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]
        used_players = set()

        for i, position in enumerate(positions):
            self.position_dropdowns[i].setCurrentText(position)
            self.update_player_dropdown(i)
            for index in range(self.player_dropdowns[i].count()):
                player_id = self.player_dropdowns[i].itemData(index)
                if player_id not in used_players:
                    self.player_dropdowns[i].setCurrentIndex(index)
                    used_players.add(player_id)
                    if position in self.position_labels:
                        self.position_labels[position].setText(self.players_dict.get(player_id, {}).get("name", ""))
                    break

    def save_lineup(self):
        # Validate that each player is eligible for their selected position
        for i in range(9):
            player_id = self.player_dropdowns[i].currentData()
            position = self.position_dropdowns[i].currentText()

            if not player_id:
                QMessageBox.warning(self, "Validation Error", f"Lineup slot {i + 1} is empty.")
                return

            pdata = self.players_dict.get(player_id)
            if not pdata:
                QMessageBox.warning(self, "Validation Error", f"Player ID {player_id} not found.")
                return

            if position == "DH":
                if pdata.get("is_pitcher"):
                    QMessageBox.warning(self, "Validation Error", f"{pdata['name']} cannot be the DH.")
                    return
            else:
                primary = pdata.get("primary_position")
                others = pdata.get("other_positions", [])
                if position != primary and position not in others:
                    QMessageBox.warning(self, "Validation Error", f"{pdata['name']} is not eligible to play {position}.")
                    return

        filename = Path(self.get_lineup_filename())
        filename.parent.mkdir(parents=True, exist_ok=True)
        for lbl in self.position_labels.values():
            lbl.setText("")
        with filename.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["order", "player_id", "position"])
            for i in range(9):
                player_id = self.player_dropdowns[i].currentData()
                position = self.position_dropdowns[i].currentText()
                writer.writerow([i + 1, player_id, position])
                if position in self.position_labels:
                    self.position_labels[position].setText(self.players_dict.get(player_id, {}).get("name", ""))

        QMessageBox.information(self, "Lineup Saved", "Lineup saved successfully.")

    def load_players_dict(self):
        players_file = get_base_dir() / "data" / "players.csv"
        players = {}
        if players_file.exists():
            with players_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    player_id = str(row.get("player_id", "")).strip()
                    name = f"{row.get('first_name', '').strip()} {row.get('last_name', '').strip()}"
                    primary = row.get("primary_position", "").strip()
                    others = (
                        row.get("other_positions", "").strip().split("|")
                        if row.get("other_positions")
                        else []
                    )
                    is_pitcher = row.get("is_pitcher") == "1"
                    players[player_id] = {
                        "name": f"{name} ({primary})",
                        "primary_position": primary,
                        "other_positions": others,
                        "is_pitcher": is_pitcher,
                        "ratings": {
                            "CH": row.get("CH", ""),
                            "PH": row.get("PH", ""),
                            "SP": row.get("SP", "")
                        }
                    }
        return players

    def get_act_level_ids(self):
        act_ids = set()
        act_roster_file = get_base_dir() / "data" / "rosters" / f"{self.team_id}.csv"
        if act_roster_file.exists():
            with act_roster_file.open("r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[1].strip().upper() == "ACT":
                        act_ids.add(row[0].strip())
        return act_ids

    def switch_view(self):
        self.current_view = self.view_selector.currentText()
        self.load_lineup()
        self.update_bench_display()

    def get_lineup_filename(self):
        """Return path to the lineup CSV for the current view.

        Lineup files live in ``data/lineups`` with names like
        ``TEAM_vs_lhp.csv`` or ``TEAM_vs_rhp.csv`` and use the columns
        ``order,player_id,position``.
        """
        suffix = "vs_lhp" if self.current_view == "vs LHP" else "vs_rhp"
        return get_base_dir() / "data" / "lineups" / f"{self.team_id}_{suffix}.csv"

    def load_lineup(self):
        for lbl in self.position_labels.values():
            lbl.setText("")
        filename = self.get_lineup_filename()
        if not Path(filename).exists():
            return

        with Path(filename).open("r", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    i = int(row.get("order", 0)) - 1
                except (TypeError, ValueError):
                    continue
                if not 0 <= i < 9:
                    continue
                player_id = row.get("player_id", "").strip()
                position = row.get("position", "").strip()
                self.position_dropdowns[i].setCurrentText(position)
                self.update_player_dropdown(i)
                for index in range(self.player_dropdowns[i].count()):
                    if self.player_dropdowns[i].itemData(index) == player_id:
                        self.player_dropdowns[i].setCurrentIndex(index)
                        if position in self.position_labels:
                            self.position_labels[position].setText(self.players_dict.get(player_id, {}).get("name", ""))
                        break

    def update_bench_display(self):
        used_ids = {self.player_dropdowns[i].currentData() for i in range(9)}
        bench_players = sorted(
            [
                pdata["name"]
                for pid, pdata in self.players_dict.items()
                if pid in self.act_level_ids
                and pid not in used_ids
                and not get_role(pdata)
            ]
        )

        self.bench_display.clear()
        if bench_players:
            self.bench_display.addItems(bench_players)
        else:
            self.bench_display.addItem("(none)")

    def update_overlay_label(self, index):
        position = self.position_dropdowns[index].currentText()
        player_id = self.player_dropdowns[index].currentData()
        if position in self.position_labels:
            label = self.position_labels[position]
            new_name = self.players_dict.get(player_id, {}).get("name", "")

            animation = QPropertyAnimation(label, b"windowOpacity")
            animation.setDuration(200)
            animation.setStartValue(1.0)
            animation.setEndValue(0.0)

            def set_text_and_fade_in():
                label.setText(new_name)
                fade_in = QPropertyAnimation(label, b"windowOpacity")
                fade_in.setDuration(200)
                fade_in.setStartValue(0.0)
                fade_in.setEndValue(1.0)
                fade_in.start()
                label.fade_in_anim = fade_in  # prevent garbage collection

            animation.finished.connect(set_text_and_fade_in)
            animation.start()
            label.fade_out_anim = animation  # prevent garbage collection

    def clear_lineup(self):
        for i in range(9):
            self.player_dropdowns[i].setCurrentIndex(-1)
            self.position_dropdowns[i].setCurrentIndex(0)
        for lbl in self.position_labels.values():
            lbl.setText("")
        self.update_bench_display()

    def update_player_dropdown(self, index):
        selected_pos = self.position_dropdowns[index].currentText()
        dropdown = self.player_dropdowns[index]
        dropdown.clear()
        for pid, pdata in self.players_dict.items():
            if pid not in self.act_level_ids:
                continue
            primary = pdata.get("primary_position")
            others = pdata.get("other_positions", [])
            if selected_pos == "DH":
                if not pdata.get("is_pitcher"):
                    dropdown.addItem(pdata["name"], userData=pid)
            elif selected_pos == primary or selected_pos in others:
                dropdown.addItem(pdata["name"], userData=pid)
