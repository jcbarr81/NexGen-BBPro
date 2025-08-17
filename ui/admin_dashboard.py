from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QDialog,
    QListWidget,
    QHBoxLayout,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QComboBox,
    QMenuBar,
    QApplication,
    QProgressDialog,
)
from PyQt6.QtCore import Qt
from ui.team_entry_dialog import TeamEntryDialog
from ui.exhibition_game_dialog import ExhibitionGameDialog
from utils.trade_utils import load_trades, save_trade
from utils.news_logger import log_news_event
from utils.roster_loader import load_roster
from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.user_manager import add_user, load_users, update_user
from utils.avatar_generator import generate_avatar
from models.trade import Trade
import csv
import os
from logic.league_creator import create_league

class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard")
        # Use a modest default size so the dashboard doesn't fill the screen
        # when launched.
        self.setGeometry(200, 200, 800, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        menubar = QMenuBar()
        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)
        layout.setMenuBar(menubar)

        header = QLabel("Welcome to the Admin Dashboard")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        layout.addStretch()

        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)

        self.review_button = QPushButton("Review Trades")
        self.review_button.clicked.connect(self.open_trade_review)
        button_layout.addWidget(self.review_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.create_league_button = QPushButton("Create League")
        self.create_league_button.clicked.connect(self.open_create_league)
        button_layout.addWidget(self.create_league_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.add_user_button = QPushButton("Add User")
        self.add_user_button.clicked.connect(self.open_add_user)
        button_layout.addWidget(self.add_user_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.edit_user_button = QPushButton("Edit User")
        self.edit_user_button.clicked.connect(self.open_edit_user)
        button_layout.addWidget(self.edit_user_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.generate_logos_button = QPushButton("Generate Team Logos")
        self.generate_logos_button.clicked.connect(self.generate_team_logos)
        button_layout.addWidget(self.generate_logos_button, alignment=Qt.AlignmentFlag.AlignHCenter)


        self.generate_avatars_button = QPushButton("Generate Player Avatars")
        self.generate_avatars_button.clicked.connect(self.generate_player_avatars)
        button_layout.addWidget(self.generate_avatars_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.exhibition_button = QPushButton("Simulate Exhibition Game")
        self.exhibition_button.clicked.connect(self.open_exhibition_dialog)
        button_layout.addWidget(self.exhibition_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addLayout(button_layout)
        layout.addStretch()

        self.setStyleSheet(
            """
            QWidget {background-color: #f0f0f0; color: #000000; font-size: 14px;}
            QPushButton {padding: 8px;}
            """
        )

        self.setLayout(layout)

    def open_trade_review(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Review Pending Trades")
        dialog.setMinimumSize(600, 400)

        trades = load_trades()
        players = {p.player_id: p for p in load_players_from_csv("data/players.csv")}
        teams = {t.team_id: t for t in load_teams("data/teams.csv")}

        layout = QVBoxLayout()

        trade_list = QListWidget()
        trade_map = {}

        for t in trades:
            if t.status != "pending":
                continue
            give_names = [f"{pid} ({players[pid].first_name} {players[pid].last_name})" for pid in t.give_player_ids if pid in players]
            recv_names = [f"{pid} ({players[pid].first_name} {players[pid].last_name})" for pid in t.receive_player_ids if pid in players]
            summary = f"{t.trade_id}: {t.from_team} → {t.to_team} | Give: {', '.join(give_names)} | Get: {', '.join(recv_names)}"
            trade_list.addItem(summary)
            trade_map[summary] = t

        def process_trade(accept=True):
            selected = trade_list.currentItem()
            if not selected:
                return
            summary = selected.text()
            trade = trade_map[summary]

            # Update rosters
            from_roster = load_roster(trade.from_team)
            to_roster = load_roster(trade.to_team)

            for pid in trade.give_player_ids:
                for level in ["act", "aaa", "low"]:
                    if pid in getattr(from_roster, level):
                        getattr(from_roster, level).remove(pid)
                        getattr(to_roster, level).append(pid)
                        break

            for pid in trade.receive_player_ids:
                for level in ["act", "aaa", "low"]:
                    if pid in getattr(to_roster, level):
                        getattr(to_roster, level).remove(pid)
                        getattr(from_roster, level).append(pid)
                        break

            # Save updated rosters
            def save_roster(roster):
                path = f"data/rosters/{roster.team_id}.csv"
                with open(path, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["player_id", "level"])
                    writer.writeheader()
                    for lvl in ["act", "aaa", "low"]:
                        for pid in getattr(roster, lvl):
                            writer.writerow({"player_id": pid, "level": lvl.upper()})

            save_roster(from_roster)
            save_roster(to_roster)

            # Update trade status
            trade.status = "accepted" if accept else "rejected"
            save_trade(trade)

            log_news_event(f"TRADE {'ACCEPTED' if accept else 'REJECTED'}: {summary}")
            QMessageBox.information(dialog, "Trade Processed", f"{summary} marked as {trade.status.upper()}.")
            trade_list.takeItem(trade_list.currentRow())

        btn_layout = QHBoxLayout()
        accept_btn = QPushButton("Accept Trade")
        reject_btn = QPushButton("Reject Trade")
        accept_btn.clicked.connect(lambda: process_trade(True))
        reject_btn.clicked.connect(lambda: process_trade(False))
        btn_layout.addWidget(accept_btn)
        btn_layout.addWidget(reject_btn)

        layout.addWidget(trade_list)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def generate_team_logos(self):
        teams = load_teams("data/teams.csv")
        progress = QProgressDialog(
            "Generating team logos...",
            None,
            0,
            len(teams),
            self,
        )
        progress.setWindowTitle("Generating Logos")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        def cb(done: int, total: int) -> None:
            progress.setValue(done)
            QApplication.processEvents()

        try:
            from utils.logo_generator import generate_team_logos
            out_dir = generate_team_logos(progress_callback=cb)
            QMessageBox.information(
                self,
                "Logos Generated",
                f"Team logos created in: {out_dir}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate logos: {e}")
        finally:
            progress.close()
        return

    def generate_player_avatars(self):
        players = load_players_from_csv("data/players.csv")
        progress = QProgressDialog(
            "Generating player avatars...",
            None,
            0,
            len(players),
            self,
        )
        progress.setWindowTitle("Generating Avatars")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        try:
            for idx, player in enumerate(players, start=1):
                out_path = os.path.join("images", "avatars", f"{player.player_id}.png")
                generate_avatar(f"{player.first_name} {player.last_name}", player.team_id, out_path)
                progress.setValue(idx)
                QApplication.processEvents()
            QMessageBox.information(self, "Avatars Generated", "Player avatars created.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate avatars: {e}")
        finally:
            progress.close()
        return

    def open_exhibition_dialog(self):
        dialog = ExhibitionGameDialog(self)
        dialog.exec()

    def open_add_user(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add User")

        layout = QVBoxLayout()

        username_input = QLineEdit()
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        team_combo = QComboBox()


        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        teams = load_teams(os.path.join(data_dir, "teams.csv"))
        for t in teams:
            team_combo.addItem(f"{t.name} ({t.team_id})", userData=t.team_id)

        layout.addWidget(QLabel("Username:"))
        layout.addWidget(username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(password_input)
        layout.addWidget(QLabel("Team:"))
        layout.addWidget(team_combo)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def handle_add():
            username = username_input.text().strip()
            password = password_input.text().strip()
            team_id = team_combo.currentData()
            if not username or not password:
                QMessageBox.warning(dialog, "Error", "Username and password required.")
                return
            try:
                add_user(username, password, "owner", team_id)
            except ValueError as e:
                QMessageBox.warning(dialog, "Error", str(e))
                return
            QMessageBox.information(dialog, "Success", f"User {username} added.")
            dialog.accept()

        add_btn.clicked.connect(handle_add)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.setLayout(layout)
        dialog.exec()

    def open_edit_user(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit User")

        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        users = load_users(os.path.join(data_dir, "users.txt"))
        if not users:
            QMessageBox.information(self, "No Users", "No users available.")
            return

        layout = QVBoxLayout()

        user_combo = QComboBox()
        for u in users:
            user_combo.addItem(u["username"], userData=u)

        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)

        team_combo = QComboBox()
        teams = load_teams(os.path.join(data_dir, "teams.csv"))
        team_combo.addItem("None", "")
        for t in teams:
            team_combo.addItem(f"{t.name} ({t.team_id})", userData=t.team_id)

        layout.addWidget(QLabel("User:"))
        layout.addWidget(user_combo)
        layout.addWidget(QLabel("New Password:"))
        layout.addWidget(password_input)
        layout.addWidget(QLabel("Team:"))
        layout.addWidget(team_combo)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Update")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def sync_fields():
            user = user_combo.currentData()
            index = team_combo.findData(user["team_id"])
            if index >= 0:
                team_combo.setCurrentIndex(index)
            password_input.clear()

        user_combo.currentIndexChanged.connect(sync_fields)
        sync_fields()

        def handle_update():
            user = user_combo.currentData()
            new_password = password_input.text().strip() or None
            new_team = team_combo.currentData()
            try:
                update_user(
                    user["username"],
                    new_password,
                    new_team,
                    os.path.join(data_dir, "users.txt"),
                )
            except ValueError as e:
                QMessageBox.warning(dialog, "Error", str(e))
                return
            QMessageBox.information(dialog, "Success", f"User {user['username']} updated.")
            dialog.accept()

        save_btn.clicked.connect(handle_update)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.setLayout(layout)
        dialog.exec()

    def open_create_league(self):
        confirm = QMessageBox.question(
            self,
            "Overwrite Existing League?",
            "Creating a new league will overwrite the current league and teams. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        league_name, ok = QInputDialog.getText(
            self, "League Name", "Enter league name:"
        )
        if not ok or not league_name:
            return
        league_name = league_name.strip()

        div_text, ok = QInputDialog.getText(
            self, "Divisions", "Enter division names separated by commas:"
        )
        if not ok or not div_text:
            return
        divisions = [d.strip() for d in div_text.split(",") if d.strip()]
        if not divisions:
            return

        teams_per_div, ok = QInputDialog.getInt(
            self, "Teams", "Teams per division:", 2, 1, 20
        )
        if not ok:
            return

        dialog = TeamEntryDialog(divisions, teams_per_div, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        structure = dialog.get_structure()
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        try:
            create_league(data_dir, structure, league_name)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to purge existing league: {e}")
            return
        QMessageBox.information(self, "League Created", "New league generated.")
