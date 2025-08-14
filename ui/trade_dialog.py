from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from models.trade import Trade
from utils.player_loader import load_players_from_csv
from utils.roster_loader import load_roster, save_roster
from utils.team_loader import load_teams
from utils.trade_utils import get_pending_trades, save_trade

import uuid


class TradeDialog(QDialog):
    """Dialog allowing an owner to propose and respond to trades."""

    def __init__(self, team_id: str, parent=None):
        super().__init__(parent)
        self.team_id = team_id
        self.players = {p.player_id: p for p in load_players_from_csv("data/players.csv")}

        self.setWindowTitle("Trade Center")
        self.resize(600, 400)

        tabs = QTabWidget()
        tabs.addTab(self._build_new_trade_tab(), "New Trade")
        tabs.addTab(self._build_incoming_tab(), "Incoming")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

    # --- New trade tab -------------------------------------------------
    def _build_new_trade_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Trade with:"))
        self.team_dropdown = QComboBox()
        teams = [t.team_id for t in load_teams() if t.team_id != self.team_id]
        self.team_dropdown.addItems(teams)
        self.team_dropdown.currentTextChanged.connect(self._refresh_receive_list)
        layout.addWidget(self.team_dropdown)

        layout.addWidget(QLabel("Players to Give"))
        self.give_list = QListWidget()
        self.give_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        roster = load_roster(self.team_id)
        for pid in roster.act:
            self.give_list.addItem(self._make_player_item(pid))
        layout.addWidget(self.give_list)

        layout.addWidget(QLabel("Players to Receive"))
        self.receive_list = QListWidget()
        self.receive_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.receive_list)
        self._refresh_receive_list(self.team_dropdown.currentText())

        submit_btn = QPushButton("Submit Trade")
        submit_btn.clicked.connect(self._submit_trade)
        layout.addWidget(submit_btn)

        return widget

    def _make_player_item(self, pid: str) -> QListWidgetItem:
        p = self.players.get(pid)
        label = f"{p.first_name} {p.last_name} ({pid})" if p else pid
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, pid)
        return item

    def _refresh_receive_list(self, team_id: str):
        self.receive_list.clear()
        if not team_id:
            return
        roster = load_roster(team_id)
        for pid in roster.act:
            self.receive_list.addItem(self._make_player_item(pid))

    def _submit_trade(self):
        to_team = self.team_dropdown.currentText()
        give_items = self.give_list.selectedItems()
        recv_items = self.receive_list.selectedItems()
        if not to_team or not give_items or not recv_items:
            QMessageBox.warning(self, "Incomplete", "Select players to trade.")
            return
        give_ids = [i.data(Qt.ItemDataRole.UserRole) for i in give_items]
        recv_ids = [i.data(Qt.ItemDataRole.UserRole) for i in recv_items]
        trade = Trade(
            trade_id=uuid.uuid4().hex[:8],
            from_team=self.team_id,
            to_team=to_team,
            give_player_ids=give_ids,
            receive_player_ids=recv_ids,
        )
        save_trade(trade)
        QMessageBox.information(self, "Trade Sent", f"Trade proposal sent to {to_team}.")
        self.give_list.clearSelection()
        self.receive_list.clearSelection()

    # --- Incoming trades tab -------------------------------------------
    def _build_incoming_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.incoming_list = QListWidget()
        layout.addWidget(self.incoming_list)

        btn_row = QHBoxLayout()
        accept_btn = QPushButton("Accept")
        reject_btn = QPushButton("Reject")
        accept_btn.clicked.connect(lambda: self._respond_to_trade(True))
        reject_btn.clicked.connect(lambda: self._respond_to_trade(False))
        btn_row.addWidget(accept_btn)
        btn_row.addWidget(reject_btn)
        layout.addLayout(btn_row)

        self._load_incoming_trades()
        return widget

    def _load_incoming_trades(self):
        self.trade_map: Dict[str, Trade] = {}
        self.incoming_list.clear()
        for t in get_pending_trades(self.team_id):
            give_names = [self.players.get(pid).last_name for pid in t.give_player_ids if pid in self.players]
            recv_names = [self.players.get(pid).last_name for pid in t.receive_player_ids if pid in self.players]
            summary = f"{t.trade_id}: {t.from_team} → {t.to_team} | Give: {', '.join(give_names)} | Get: {', '.join(recv_names)}"
            self.incoming_list.addItem(summary)
            self.trade_map[summary] = t

    def _respond_to_trade(self, accept: bool):
        selected = self.incoming_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a trade to respond to.")
            return
        trade = self.trade_map[selected.text()]
        trade.status = "accepted" if accept else "rejected"
        if accept:
            self._process_trade(trade)
        save_trade(trade)
        QMessageBox.information(self, "Trade Updated", f"Trade {trade.trade_id} {trade.status}.")
        self.incoming_list.takeItem(self.incoming_list.currentRow())

    def _process_trade(self, trade: Trade):
        from_roster = load_roster(trade.from_team)
        to_roster = load_roster(trade.to_team)
        for pid in trade.give_player_ids:
            for roster in (from_roster, to_roster):
                if pid in roster.act:
                    roster.act.remove(pid)
            to_roster.act.append(pid)
        for pid in trade.receive_player_ids:
            for roster in (from_roster, to_roster):
                if pid in roster.act:
                    roster.act.remove(pid)
            from_roster.act.append(pid)
        save_roster(trade.from_team, from_roster)
        save_roster(trade.to_team, to_roster)
