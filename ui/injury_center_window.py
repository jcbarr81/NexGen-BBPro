from __future__ import annotations

"""Injury Center (read-only).

Displays a consolidated view of injured players across all teams with the
team assignment, injury list (DL/IR), description and expected return date.
This is a viewer-only tool; roster changes are handled elsewhere.
"""

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QAbstractItemView,
        QLineEdit,
        QComboBox,
    )
    from PyQt6.QtCore import Qt
except Exception:  # pragma: no cover - headless stubs for tests
    class _Signal:
        def __init__(self): self._s=None
        def connect(self, s): self._s=s
        def emit(self,*a,**k):
            if self._s: self._s(*a,**k)
    class QDialog:
        def __init__(self,*a,**k): pass
        def show(self): pass
    class QLabel:
        def __init__(self, t="", *a, **k): self._t=t
        def setText(self, t): self._t=t
    class QPushButton:
        def __init__(self,*a,**k): self.clicked=_Signal()
    class QTableWidget:
        def __init__(self,*a,**k): pass
        def setHorizontalHeaderLabels(self,*a,**k): pass
        def setRowCount(self,*a,**k): pass
        def setItem(self,*a,**k): pass
        def setEditTriggers(self,*a,**k): pass
        def setSelectionBehavior(self,*a,**k): pass
        def setSelectionMode(self,*a,**k): pass
    class QTableWidgetItem:
        def __init__(self, t=""): self._t=str(t)
        def text(self): return self._t
    class QVBoxLayout:
        def __init__(self,*a,**k): pass
        def addWidget(self,*a,**k): pass
        def addLayout(self,*a,**k): pass
        def setContentsMargins(self,*a,**k): pass
        def setSpacing(self,*a,**k): pass
    class QHBoxLayout(QVBoxLayout): pass
    class QAbstractItemView:
        class EditTrigger: NoEditTriggers=0
        class SelectionBehavior: SelectRows=0
        class SelectionMode: SingleSelection=0
    class Qt:
        class AlignmentFlag: AlignLeft=0; AlignHCenter=0
    class QLineEdit:
        def __init__(self,*a,**k): self._t=""
        def text(self): return self._t
        def setText(self, t): self._t=t
    class QComboBox:
        def __init__(self,*a,**k): self._items=[]; self._idx=0
        def addItems(self, items): self._items=list(items)
        def currentText(self):
            return self._items[self._idx] if self._items else ""

from typing import Dict, List, Tuple
from datetime import datetime

from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.roster_loader import load_roster
from utils.roster_loader import save_roster
from utils.player_writer import save_players_to_csv
from services.injury_manager import place_on_injury_list, recover_from_injury
from utils.news_logger import log_news_event
try:
    from services.roster_auto_assign import ACTIVE_MAX, AAA_MAX, LOW_MAX
except Exception:  # sensible defaults
    ACTIVE_MAX, AAA_MAX, LOW_MAX = 25, 15, 10


class InjuryCenterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Injury Center")
            self.resize(900, 600)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        self.title = QLabel("Injured Players")
        header.addWidget(self.title)
        header.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Player", "Team", "List", "Position", "Description", "Return Date"])
        try:
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        except Exception:
            pass
        root.addWidget(self.table)

        # Actions row
        actions = QHBoxLayout()
        actions.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        try:
            self.desc_edit.setPlaceholderText("e.g., Hamstring strain")
        except Exception:
            pass
        actions.addWidget(self.desc_edit)
        actions.addWidget(QLabel("Return (YYYY-MM-DD):"))
        self.ret_edit = QLineEdit()
        try:
            self.ret_edit.setPlaceholderText("YYYY-MM-DD (optional)")
            self.ret_edit.setToolTip("Enter return date in YYYY-MM-DD format. Leave blank if unknown.")
        except Exception:
            pass
        actions.addWidget(self.ret_edit)
        actions.addWidget(QLabel("Destination:"))
        self.dest_combo = QComboBox()
        try:
            self.dest_combo.addItems(["Active (ACT)", "AAA", "Low"])
            self.dest_combo.setToolTip("Level to place player on recovery")
        except Exception:
            pass
        actions.addWidget(self.dest_combo)
        self.btn_place_dl = QPushButton("Place on DL")
        self.btn_place_ir = QPushButton("Place on IR")
        self.btn_recover = QPushButton("Recover to Destination")
        self.btn_promote_best = QPushButton("Promote Best Replacement")
        self.role_hint_label = QLabel("Recommended: --")
        try:
            self.role_hint_label.setStyleSheet("color: #888888; font-size: 11px;")
        except Exception:
            pass
        try:
            self.btn_place_dl.clicked.connect(lambda: self._place_on_list("dl"))
            self.btn_place_ir.clicked.connect(lambda: self._place_on_list("ir"))
            self.btn_recover.clicked.connect(self._recover)
            # Live date validation styling
            self.ret_edit.textChanged.connect(self._on_date_changed)
            self.btn_promote_best.clicked.connect(self._promote_best)
        except Exception:
            pass
        actions.addWidget(self.btn_place_dl)
        actions.addWidget(self.btn_place_ir)
        actions.addWidget(self.btn_recover)
        actions.addWidget(self.btn_promote_best)
        actions.addWidget(self.role_hint_label)
        root.addLayout(actions)

        # Roster counts indicator
        counts_row = QHBoxLayout()
        counts_row.addWidget(QLabel("Roster Counts:"))
        self.counts_label = QLabel("ACT --/--  AAA --/--  LOW --/--")
        counts_row.addWidget(self.counts_label)
        counts_row.addStretch()
        root.addLayout(counts_row)

        # Tiny legend for limits and FULL marker
        try:
            self.counts_legend = QLabel(
                f"Legend: FULL denotes at/over capacity. Limits ACT {ACTIVE_MAX}, AAA {AAA_MAX}, LOW {LOW_MAX}."
            )
            try:
                self.counts_legend.setWordWrap(True)
                self.counts_legend.setStyleSheet("color: #888888; font-size: 11px;")
            except Exception:
                pass
            root.addWidget(self.counts_legend)
        except Exception:
            pass

        self.status = QLabel("Ready")
        root.addWidget(self.status)

        self._players_index: Dict[str, object] = {}
        self._rows: List[Dict[str, str]] = []
        self.refresh()

    def refresh(self) -> None:
        # Build map from player -> (team_id, list_name)
        injury_map: Dict[str, Tuple[str, str]] = {}
        try:
            teams = load_teams()
        except Exception:
            teams = []
        for t in teams:
            try:
                r = load_roster(t.team_id)
            except Exception:
                continue
            for pid in getattr(r, 'dl', []) or []:
                injury_map[pid] = (t.team_id, 'DL')
            for pid in getattr(r, 'ir', []) or []:
                injury_map[pid] = (t.team_id, 'IR')

        # Load player details and filter
        try:
            players = load_players_from_csv("data/players.csv")
        except Exception:
            players = []
        injured: List[object] = []
        self._players_index = {getattr(p, 'player_id', ''): p for p in players}
        for p in players:
            if getattr(p, 'injured', False) or getattr(p, 'player_id', '') in injury_map:
                injured.append(p)

        # Fill table
        self.table.setRowCount(len(injured))
        self._rows = []
        for row, p in enumerate(injured):
            pid = getattr(p, 'player_id', '')
            name = f"{getattr(p,'first_name','')} {getattr(p,'last_name','')}".strip()
            team_id, list_name = injury_map.get(pid, ("", ""))
            pos = getattr(p, 'primary_position', '')
            desc = getattr(p, 'injury_description', '') or ""
            ret = getattr(p, 'return_date', '') or ""
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(team_id))
            self.table.setItem(row, 2, QTableWidgetItem(list_name))
            self.table.setItem(row, 3, QTableWidgetItem(str(pos)))
            self.table.setItem(row, 4, QTableWidgetItem(desc))
            self.table.setItem(row, 5, QTableWidgetItem(ret))
            self._rows.append({"player_id": pid, "team_id": team_id, "list": list_name})
        self.status.setText(f"Showing {len(injured)} injured players")
        # Update counts if a row is selected
        try:
            self.table.itemSelectionChanged.connect(self._on_selection_changed)
        except Exception:
            pass
        self._on_selection_changed()

    # ------------------------------------------------------------------
    # Actions
    def _set_field_valid(self, widget, valid: bool) -> None:
        try:
            if valid:
                widget.setStyleSheet("")
            else:
                widget.setStyleSheet("border: 1px solid #cc4455;")
        except Exception:
            pass

    def _on_date_changed(self) -> None:
        try:
            txt = (self.ret_edit.text() or "").strip()
        except Exception:
            txt = ""
        ok = self._validate_iso_date(txt)
        self._set_field_valid(self.ret_edit, ok)
        if not ok:
            try:
                self.status.setText("Return date must be YYYY-MM-DD")
            except Exception:
                pass
    def _validate_iso_date(self, s: str) -> bool:
        s = (s or "").strip()
        if not s:
            return True
        try:
            # Accept strict YYYY-MM-DD
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except Exception:
            return False
    def _selected(self) -> Tuple[str | None, str | None]:
        row = getattr(self.table, 'currentRow', lambda: -1)()
        if row is None or row < 0 or row >= len(self._rows):
            return None, None
        return self._rows[row].get("player_id"), self._rows[row].get("team_id")

    def _update_counts(self, team_id: str | None) -> None:
        if not team_id:
            try:
                self.counts_label.setText(f"ACT --/{ACTIVE_MAX}  AAA --/{AAA_MAX}  LOW --/{LOW_MAX}")
                self.counts_label.setStyleSheet("")
            except Exception:
                pass
            return
        try:
            r = load_roster(team_id)
        except Exception:
            try:
                self.counts_label.setText(f"ACT ?/{ACTIVE_MAX}  AAA ?/{AAA_MAX}  LOW ?/{LOW_MAX}")
                self.counts_label.setStyleSheet("color: #cc8844;")
            except Exception:
                pass
            return
        act, aaa, low = len(getattr(r, 'act', []) or []), len(getattr(r, 'aaa', []) or []), len(getattr(r, 'low', []) or [])
        # Append FULL marker for any level at or above capacity
        act_mark = " (FULL)" if act >= ACTIVE_MAX else ""
        aaa_mark = " (FULL)" if aaa >= AAA_MAX else ""
        low_mark = " (FULL)" if low >= LOW_MAX else ""
        text = f"ACT {act}/{ACTIVE_MAX}{act_mark}  AAA {aaa}/{AAA_MAX}{aaa_mark}  LOW {low}/{LOW_MAX}{low_mark}"
        try:
            self.counts_label.setText(text)
            # Visual warning: orange when any level is at/over capacity; else default
            if act >= ACTIVE_MAX or aaa >= AAA_MAX or low >= LOW_MAX:
                self.counts_label.setStyleSheet("color: #cc8844; font-weight: 600;")
            else:
                self.counts_label.setStyleSheet("")
        except Exception:
            pass

    def _on_selection_changed(self) -> None:
        pid, team_id = self._selected()
        self._update_counts(team_id)
        # Update role hint
        try:
            p = self._players_index.get(pid or "")
            if p is not None:
                is_pitcher = bool(getattr(p, 'is_pitcher', False) or str(getattr(p, 'primary_position', '')).upper() == 'P')
                hint = "Pitcher" if is_pitcher else "Hitter"
                self.role_hint_label.setText(f"Recommended: {hint}")
            else:
                self.role_hint_label.setText("Recommended: --")
        except Exception:
            pass

    def _find_team_and_roster(self, pid: str) -> Tuple[str | None, object | None]:
        try:
            teams = load_teams()
        except Exception:
            teams = []
        for t in teams:
            try:
                r = load_roster(t.team_id)
            except Exception:
                continue
            for level in ("act", "aaa", "low", "dl", "ir"):
                if pid in getattr(r, level):
                    return t.team_id, r
        return None, None

    def _place_on_list(self, list_name: str) -> None:
        pid, team_hint = self._selected()
        if not pid:
            self.status.setText("Select a player first.")
            return
        player = self._players_index.get(pid)
        if player is None:
            self.status.setText("Player not found in database.")
            return
        team_id, roster = (team_hint, None)
        if not team_id:
            team_id, roster = self._find_team_and_roster(pid)
        if not team_id:
            self.status.setText("Could not determine player's team.")
            return
        if roster is None:
            try:
                roster = load_roster(team_id)
            except Exception as exc:
                self.status.setText(f"Failed to load roster: {exc}")
                return
        # Update player injury fields
        try:
            place_on_injury_list(player, roster, list_name)
            desc = self.desc_edit.text().strip()
            ret = self.ret_edit.text().strip()
            if not self._validate_iso_date(ret):
                self.status.setText("Return date must be YYYY-MM-DD")
                return
            try:
                player.injured = True
                player.injury_description = desc or player.injury_description
                player.return_date = ret or player.return_date
            except Exception:
                pass
            # Persist roster and players.csv
            save_roster(team_id, roster)
            try:
                # Rewrite players.csv with updated fields
                plist = list(load_players_from_csv("data/players.csv"))
                # Replace matching player object by id
                for i, p in enumerate(plist):
                    if getattr(p, 'player_id', '') == pid:
                        plist[i] = player
                        break
                from utils.path_utils import get_base_dir
                save_players_to_csv(plist, str(get_base_dir() / 'data' / 'players.csv'))
            except Exception:
                pass
            # Clear caches
            try:
                load_roster.cache_clear()
            except Exception:
                pass
            try:
                load_players_from_csv.cache_clear()
            except Exception:
                pass
            log_news_event(f"Placed {getattr(player,'first_name','')} {getattr(player,'last_name','')} on {list_name.upper()} ({team_id})")
            self.refresh()
        except Exception as exc:
            self.status.setText(f"Failed: {exc}")

    def _recover(self) -> None:
        pid, team_hint = self._selected()
        if not pid:
            self.status.setText("Select a player first.")
            return
        player = self._players_index.get(pid)
        if player is None:
            self.status.setText("Player not found in database.")
            return
        team_id, roster = (team_hint, None)
        if not team_id:
            team_id, roster = self._find_team_and_roster(pid)
        if not team_id:
            self.status.setText("Could not determine player's team.")
            return
        if roster is None:
            try:
                roster = load_roster(team_id)
            except Exception as exc:
                self.status.setText(f"Failed to load roster: {exc}")
                return
        try:
            # Destination mapping
            dest_label = ""
            try:
                dest_label = (self.dest_combo.currentText() or "").lower()
            except Exception:
                dest_label = "active (act)"
            dest = "act"
            if "aaa" in dest_label:
                dest = "aaa"
            elif "low" in dest_label:
                dest = "low"
            recover_from_injury(player, roster, destination=dest)
            try:
                player.injured = False
                player.injury_description = None
                player.return_date = None
            except Exception:
                pass
            save_roster(team_id, roster)
            try:
                plist = list(load_players_from_csv("data/players.csv"))
                for i, p in enumerate(plist):
                    if getattr(p, 'player_id', '') == pid:
                        plist[i] = player
                        break
                from utils.path_utils import get_base_dir
                save_players_to_csv(plist, str(get_base_dir() / 'data' / 'players.csv'))
            except Exception:
                pass
            try:
                load_roster.cache_clear()
            except Exception:
                pass
            try:
                load_players_from_csv.cache_clear()
            except Exception:
                pass
            log_news_event(f"Activated {getattr(player,'first_name','')} {getattr(player,'last_name','')} from injury list ({team_id})")
            self.refresh()
        except Exception as exc:
            self.status.setText(f"Failed: {exc}")

    def _promote_best(self) -> None:
        # Promote best replacement from AAA/Low to ACT for the selected team
        _pid, team_id = self._selected()
        if not team_id:
            self.status.setText("Select a team row first.")
            return
        try:
            roster = load_roster(team_id)
        except Exception as exc:
            self.status.setText(f"Failed to load roster: {exc}")
            return
        if len(getattr(roster, 'act', []) or []) >= ACTIVE_MAX:
            self.status.setText(f"Active roster already at limit ({ACTIVE_MAX}).")
            return
        # Load players to score candidates
        try:
            players = load_players_from_csv("data/players.csv")
        except Exception:
            players = []
        pmap = {getattr(p, 'player_id', ''): p for p in players}
        # Decide candidate pool from AAA then Low
        pool_ids = (getattr(roster, 'aaa', []) or []) + (getattr(roster, 'low', []) or [])
        if not pool_ids:
            self.status.setText("No candidates in AAA/Low.")
            return
        # If a player is selected, prefer role-aware promotion using that player's type
        sel_pid, _ = self._selected()
        sel_obj = pmap.get(sel_pid or "")
        sel_is_pitcher = bool(getattr(sel_obj, 'is_pitcher', False) or str(getattr(sel_obj, 'primary_position', '')).upper() == 'P') if sel_obj else False

        def pitcher_score(p):
            return (float(getattr(p, 'endurance', 0)) * 0.5 + float(getattr(p, 'control', 0)) * 0.3 + float(getattr(p, 'movement', 0)) * 0.2)

        def hitter_score(p):
            keys = ['ch','ph','sp','pl','vl','sc','fa','arm']
            vals = []
            for k in keys:
                try:
                    vals.append(float(getattr(p, k, 0)))
                except Exception:
                    vals.append(0.0)
            return sum(vals)/len(vals) if vals else 0.0

        best_id = None
        best_val = -1.0
        for pid in pool_ids:
            p = pmap.get(pid)
            if not p:
                continue
            is_pitcher = bool(getattr(p, 'is_pitcher', False) or str(getattr(p, 'primary_position', '')).upper() == 'P')
            if sel_obj:
                # Role-aware: match type of injured/selected player
                if sel_is_pitcher and not is_pitcher:
                    continue
                if not sel_is_pitcher and is_pitcher:
                    continue
            score = pitcher_score(p) if is_pitcher else hitter_score(p)
            if score > best_val:
                best_val = score
                best_id = pid
        if not best_id:
            self.status.setText("No suitable candidate found.")
            return
        # Promote: remove from AAA/Low and append to ACT
        try:
            if best_id in roster.aaa:
                roster.aaa.remove(best_id)
            elif best_id in roster.low:
                roster.low.remove(best_id)
            roster.act.append(best_id)
            save_roster(team_id, roster)
            try:
                load_roster.cache_clear()
            except Exception:
                pass
            log_news_event(f"Promoted {best_id} to ACT for {team_id}")
            self.refresh()
        except Exception as exc:
            self.status.setText(f"Failed to promote: {exc}")


__all__ = ["InjuryCenterWindow"]
