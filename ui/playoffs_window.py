from __future__ import annotations

"""Playoffs viewer window.

Displays the current bracket (rounds, series, and game results). This window
is read-only and provides a Refresh button to reload state from disk. Control
actions (simulate round/remaining) are handled from Season Progress for now.
"""

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QWidget,
        QFrame,
    )
    from PyQt6.QtCore import Qt
except Exception:  # pragma: no cover - headless stubs for tests
    class _Signal:
        def __init__(self):
            self._slot = None
        def connect(self, slot):
            self._slot = slot
        def emit(self, *a, **k):
            if self._slot:
                self._slot(*a, **k)
    class QDialog:
        def __init__(self, *a, **k):
            pass
        def show(self):
            pass
    class QWidget: pass
    class QFrame(QWidget):
        class Shape: StyledPanel = 0
        def setFrameShape(self, *a, **k): pass
    class QLabel:
        def __init__(self, text="", *a, **k): self._t=text
        def setText(self, t): self._t=t
    class QPushButton:
        def __init__(self, *a, **k): self.clicked=_Signal()
    class QVBoxLayout:
        def __init__(self, *a, **k): pass
        def addWidget(self, *a, **k): pass
        def addLayout(self, *a, **k): pass
        def addStretch(self, *a, **k): pass
        def setContentsMargins(self, *a, **k): pass
        def setSpacing(self, *a, **k): pass
    class QHBoxLayout(QVBoxLayout): pass
    class QScrollArea:
        def __init__(self, *a, **k): pass
        def setWidget(self, *a, **k): pass
        def setWidgetResizable(self, *a, **k): pass
    class Qt:
        class AlignmentFlag: AlignLeft = 0; AlignTop = 0; AlignHCenter = 0

from playbalance.playoffs import load_bracket

ROUND_STAGE_ALIASES = {
    "WC": "Play-In",
    "DS": "Round 1",
    "CS": "Round 2",
    "WS": "Championship",
    "FINAL": "Championship",
    "FINALS": "Championship",
}


def _friendly_round_title(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return "Round"
    parts = name.split()
    if len(parts) == 1:
        return ROUND_STAGE_ALIASES.get(parts[0].upper(), name)
    stage_code = parts[-1].upper()
    label = ROUND_STAGE_ALIASES.get(stage_code)
    if not label:
        return name
    league = " ".join(parts[:-1]).strip()
    return f"{label} - {league}" if league else label


class PlayoffsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Playoffs")
            self.resize(900, 600)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        self.title = QLabel("Current Bracket")
        header.addWidget(self.title)
        header.addStretch()
        self.sim_round_btn = QPushButton("Simulate Round")
        self.sim_round_btn.clicked.connect(self._simulate_round)
        header.addWidget(self.sim_round_btn)
        self.sim_all_btn = QPushButton("Simulate Remaining")
        self.sim_all_btn.clicked.connect(self._simulate_all)
        header.addWidget(self.sim_all_btn)
        self.export_btn = QPushButton("Export Summary")
        self.export_btn.clicked.connect(self._export_summary)
        header.addWidget(self.export_btn)
        self.open_btn = QPushButton("Open Summary")
        self.open_btn.clicked.connect(self._open_summary)
        header.addWidget(self.open_btn)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll)

        self.container = QWidget()
        self.cv = QVBoxLayout(self.container)
        self.cv.setContentsMargins(8, 8, 8, 8)
        self.cv.setSpacing(10)
        self.scroll.setWidget(self.container)

        self._bracket = None
        self._last_summary_path = None
        self.refresh()

    def refresh(self) -> None:
        self._bracket = load_bracket()
        # Clear existing
        while getattr(self.cv, 'count', lambda: 0)():
            item = self.cv.takeAt(0)
            w = item.widget()
            if w is not None:
                try:
                    w.setParent(None)
                except Exception:
                    pass
        if not self._bracket:
            # Lazy-generate a bracket if we're in playoffs and none exists yet.
            try:
                from utils.path_utils import get_base_dir
                from playbalance.playoffs import generate_bracket, save_bracket
                from playbalance.playoffs_config import load_playoffs_config
                from utils.team_loader import load_teams
                import json as _json
                base = get_base_dir()
                standings_path = base / 'data' / 'standings.json'
                standings: dict = {}
                if standings_path.exists():
                    try:
                        standings = _json.loads(standings_path.read_text(encoding='utf-8'))
                    except Exception:
                        standings = {}
                teams = []
                try:
                    teams = load_teams()
                except Exception:
                    pass
                cfg = load_playoffs_config()
                if standings and teams:
                    b = generate_bracket(standings, teams, cfg)
                    try:
                        save_bracket(b)
                        self._bracket = b
                    except Exception:
                        pass
            except Exception:
                pass
        if not self._bracket:
            self.cv.addWidget(QLabel("No playoffs bracket found."))
            try:
                self.sim_round_btn.setEnabled(False)
                self.sim_all_btn.setEnabled(False)
            except Exception:
                pass
            return
        # Header details
        year = getattr(self._bracket, 'year', '')
        champ = getattr(self._bracket, 'champion', None) or "(TBD)"
        self.title.setText(f"Playoffs {year} — Champion: {champ}")

        for rnd in getattr(self._bracket, 'rounds', []) or []:
            box = QFrame()
            try:
                box.setFrameShape(QFrame.Shape.StyledPanel)
            except Exception:
                pass
            bv = QVBoxLayout(box)
            bv.setContentsMargins(8, 8, 8, 8)
            bv.setSpacing(6)
            raw_name = str(rnd.name)
            title = _friendly_round_title(raw_name)
            lbl = QLabel(title)
            if title != raw_name and hasattr(lbl, "setToolTip"):
                try:
                    lbl.setToolTip(raw_name)
                except Exception:
                    pass
            bv.addWidget(lbl)
            if not rnd.matchups:
                bv.addWidget(QLabel("(awaiting participants)"))
            for i, m in enumerate(rnd.matchups):
                # Compute series record for tooltip
                wins_high = 0
                wins_low = 0
                game_lines = []
                try:
                    for gi, g in enumerate(m.games):
                        res = str(getattr(g, 'result', '') or '')
                        home = getattr(g, 'home', '')
                        away = getattr(g, 'away', '')
                        if '-' in res:
                            try:
                                hs, as_ = res.split('-', 1)
                                hs, as_ = int(hs), int(as_)
                                if hs > as_:
                                    if home == m.high.team_id:
                                        wins_high += 1
                                    elif home == m.low.team_id:
                                        wins_low += 1
                                elif as_ > hs:
                                    if away == m.high.team_id:
                                        wins_high += 1
                                    elif away == m.low.team_id:
                                        wins_low += 1
                            except Exception:
                                pass
                        game_lines.append(f"G{gi+1}: {away} at {home} — {res}")
                except Exception:
                    pass
                series_note = f" (Series {wins_high}-{wins_low})" if (wins_high or wins_low) else ""
                line = QLabel(f"({m.high.seed}) {m.high.team_id} vs ({m.low.seed}) {m.low.team_id}{series_note} — Winner: {m.winner or 'TBD'}")
                try:
                    line.setToolTip("\n".join(game_lines) if game_lines else "No games played yet.")
                except Exception:
                    pass
                bv.addWidget(line)
                # List game results succinctly
                for gi, g in enumerate(m.games):
                    res = g.result or "?"
                    gl = QLabel(f"  G{gi+1}: {g.away} at {g.home} — {res}")
                    bv.addWidget(gl)
            self.cv.addWidget(box)
        self.cv.addStretch(1)

        # Enable/disable simulate buttons if champion decided
        try:
            done = bool(getattr(self._bracket, 'champion', None))
            self.sim_round_btn.setEnabled(not done)
            self.sim_all_btn.setEnabled(not done)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Simulation helpers
    def _simulate_round(self) -> None:
        from playbalance.playoffs import load_bracket, save_bracket, simulate_next_round
        year = getattr(self._bracket, "year", None)
        b = self._bracket
        if b is None and year is not None:
            b = load_bracket(year=year)
        if b is None:
            b = load_bracket()
        if not b:
            return
        try:
            b = simulate_next_round(b)
        except Exception:
            return
        try:
            save_bracket(b)
            self._bracket = b
        except Exception:
            pass
        self.refresh()

    def _simulate_all(self) -> None:
        from playbalance.playoffs import load_bracket, save_bracket, simulate_playoffs
        year = getattr(self._bracket, "year", None)
        b = self._bracket
        if b is None and year is not None:
            b = load_bracket(year=year)
        if b is None:
            b = load_bracket()
        if not b:
            return
        try:
            b = simulate_playoffs(b)
        except Exception:
            return
        try:
            save_bracket(b)
            self._bracket = b
        except Exception:
            pass
        self.refresh()

    def _export_summary(self) -> None:
        # Export a simple Markdown summary of the current bracket
        from playbalance.playoffs import load_bracket
        from utils.path_utils import get_base_dir
        from pathlib import Path
        b = load_bracket()
        if not b:
            return
        lines = []
        title = f"# Playoffs {getattr(b, 'year', '')}"
        champ = getattr(b, 'champion', None)
        if champ:
            title += f" — Champion: {champ}"
        lines.append(title)
        lines.append("")
        try:
            for rnd in getattr(b, 'rounds', []) or []:
                lines.append(f"## {_friendly_round_title(rnd.name)}")
                for m in rnd.matchups or []:
                    wins_high = 0
                    wins_low = 0
                    for g in (m.games or []):
                        res = str(getattr(g, 'result', '') or '')
                        home = getattr(g, 'home', '')
                        away = getattr(g, 'away', '')
                        if '-' in res:
                            try:
                                hs, as_ = res.split('-', 1)
                                hs, as_ = int(hs), int(as_)
                                if hs > as_:
                                    if home == m.high.team_id:
                                        wins_high += 1
                                    elif home == m.low.team_id:
                                        wins_low += 1
                                elif as_ > hs:
                                    if away == m.high.team_id:
                                        wins_high += 1
                                    elif away == m.low.team_id:
                                        wins_low += 1
                            except Exception:
                                pass
                    series = f" ({wins_high}-{wins_low})" if (wins_high or wins_low) else ""
                    lines.append(f"- ({m.high.seed}) {m.high.team_id} vs ({m.low.seed}) {m.low.team_id}{series} — Winner: {m.winner or 'TBD'}")
                    for gi, g in enumerate(m.games or []):
                        res = str(getattr(g, 'result', '') or '?')
                        path = getattr(g, 'boxscore', '') or ''
                        lines.append(f"  - G{gi+1}: {g.away} at {g.home} — {res}  {path}")
                lines.append("")
        except Exception:
            pass
        try:
            out = Path(get_base_dir()) / 'data' / f"playoffs_summary_{getattr(b, 'year', '')}.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("\n".join(lines), encoding='utf-8')
            self._last_summary_path = str(out)
        except Exception:
            self._last_summary_path = None

    def _open_summary(self) -> None:
        # Attempt to open the last exported summary; if not present, export then open
        from playbalance.playoffs import load_bracket
        from utils.path_utils import get_base_dir
        from pathlib import Path
        import os, sys, subprocess
        path = self._last_summary_path
        if not path:
            b = load_bracket()
            if not b:
                return
            out = Path(get_base_dir()) / 'data' / f"playoffs_summary_{getattr(b, 'year', '')}.md"
            if not out.exists():
                self._export_summary()
            path = str(out)
        try:
            p = Path(path)
            if not p.exists():
                return
            if os.name == 'nt':  # Windows
                try:
                    os.startfile(str(p))  # type: ignore[attr-defined]
                except Exception:
                    subprocess.Popen(['cmd', '/c', 'start', '', str(p)])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(p)])
            else:
                subprocess.Popen(['xdg-open', str(p)])
        except Exception:
            pass


__all__ = ["PlayoffsWindow"]
