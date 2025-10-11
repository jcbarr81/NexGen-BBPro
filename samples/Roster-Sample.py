from PyQt6 import QtCore, QtGui, QtWidgets
from functools import partial

# ------------------------------------------------------------
# PyQt6 single-file mockup that emulates the retro
# "Front Page Sports: Baseball" Team Roster UI.
# ------------------------------------------------------------

RETRO_GREEN = "#0f3b19"          # primary deep green background
RETRO_GREEN_DARK = "#0b2a12"     # darker panel
RETRO_GREEN_TABLE = "#164a22"    # table cell background
RETRO_BEIGE = "#d2ba8f"          # classic 90s beige
RETRO_YELLOW = "#ffd34d"         # header strip text
RETRO_TEXT = "#ffffff"           # primary white text
RETRO_CYAN = "#6ce5ff"           # numeric accent (cyan-ish)
RETRO_BORDER = "#3a5f3a"         # subtle borders

COLUMNS = [
    "NO.", "Player Name", "SLOT", "POSN", "B", "CH", "PH", "SP", "FA", "AS"
]

# Sample data from the screenshot (trim/approx). Replace with your source.
SAMPLE_ROWS = [
    [2,  "Belliard, Rafael", "Act", "2B", "R", 52, 20, 34, 49, 48],
    [4,  "Blauser, Jeff",   "Act", "SS", "R", 73, 20, 37, 49, 50],
    [8,  "Lopez, Javier",    "Act", "C",  "R", 26, 34, 29, 50, 50],
    [14, "Pendleton, Terry", "Act", "3B", "R", 36, 41, 30, 50, 50],
    [17, "O'Brien, Charlie", "Act", "RF", "R", 33, 26, 31, 50, 50],
    [18, "Gallagher, Dave",  "Act", "CF", "R", 35, 36, 41, 50, 50],
    [20, "Brounson, Jay",    "Act", "LF", "R", 33, 31, 50, 50, 50],
    [21, "Lemke, Mark",      "Act", "2B", "S", 43, 44, 43, 52, 50],
    [23, "Justice, Dave",    "Act", "RF", "L", 63, 63, 43, 52, 50],
    [24, "Sanders, Deion",   "Act", "CF", "R", 29, 41, 95, 50, 50],
    [25, "Kelly, Mike",      "Act", "C",  "R", 23, 35, 35, 50, 50],
    [28, "Tarasco, Tony",    "Act", "RF", "R", 36, 39, 45, 50, 50],
    [31, "McGriff, Fred",    "Act", "1B", "L", 66, 65, 39, 50, 50],
    [32, "Pecota, Bill",     "Act", "3B", "R", 26, 20, 46, 49, 50],
    [52, "Oliva, Jose",      "AAA", "3B", "R", 51, 20, 24, 50, 50],
]

class NumberDelegate(QtWidgets.QStyledItemDelegate):
    """Right-align numeric cells and tint them retro-cyan; leave text columns white."""
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        header = index.model().headerData(index.column(), QtCore.Qt.Orientation.Horizontal)
        is_numeric_col = header in {"NO.", "CH", "PH", "SP", "FA", "AS"}
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if is_numeric_col:
            opt.displayAlignment = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            opt.palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(RETRO_CYAN))
        else:
            opt.displayAlignment = QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            opt.palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(RETRO_TEXT))
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

class RetroHeader(QtWidgets.QWidget):
    """Header area: title + yellow subheader strip."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"background:{RETRO_GREEN}; border-bottom: 1px solid {RETRO_BORDER};")

        title = QtWidgets.QLabel("Team Roster — Atlanta Warriors")
        title_font = QtGui.QFont("Segoe UI", 16, QtGui.QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setStyleSheet("color: #ff6b6b; letter-spacing: 0.5px;")

        strip = QtWidgets.QFrame()
        strip.setStyleSheet(f"background:{RETRO_GREEN_DARK}; border: 1px solid {RETRO_BORDER};")
        strip_layout = QtWidgets.QHBoxLayout(strip)
        strip_layout.setContentsMargins(10, 6, 10, 6)
        strip_layout.setSpacing(8)

        team_line = QtWidgets.QLabel("Atlanta Warriors (0-0), NBL East")
        team_line.setStyleSheet(f"color:{RETRO_YELLOW}; font-weight:600;")
        season = QtWidgets.QLabel("Season data")
        season.setStyleSheet(f"color:{RETRO_YELLOW};")

        arrow = QtWidgets.QLabel("▲")
        arrow.setStyleSheet(f"color:{RETRO_YELLOW}; font-weight:700;")
        arrow.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

        strip_layout.addWidget(team_line, 1)
        strip_layout.addWidget(season)
        strip_layout.addStretch(1)
        strip_layout.addWidget(arrow)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)
        lay.addWidget(title)
        lay.addWidget(strip)

class RosterTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setRowCount(len(SAMPLE_ROWS))

        for r, row in enumerate(SAMPLE_ROWS):
            for c, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(val))
                if COLUMNS[c] in {"NO.", "CH", "PH", "SP", "FA", "AS"}:
                    item.setData(QtCore.Qt.ItemDataRole.DisplayRole, int(val))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.setItem(r, c, item)

        widths = [50, 220, 60, 60, 40, 60, 60, 60, 60, 60]
        for i, w in enumerate(widths):
            self.setColumnWidth(i, w)

        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.setAlternatingRowColors(False)

        self.setStyleSheet(
            f"QTableWidget {{ background:{RETRO_GREEN_TABLE}; color:{RETRO_TEXT}; gridline-color:{RETRO_BORDER}; "
            f"selection-background-color:#245b2b; selection-color:{RETRO_TEXT}; font: 12px 'Segoe UI'; }}"
            f"QHeaderView::section {{ background:{RETRO_GREEN}; color:{RETRO_TEXT}; border: 1px solid {RETRO_BORDER}; font-weight:600; }}"
            f"QScrollBar:vertical {{ background:{RETRO_GREEN_DARK}; width: 12px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background:{RETRO_BEIGE}; min-height: 24px; }}"
        )

        delegate = NumberDelegate(self)
        self.setItemDelegate(delegate)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

class StatusFooter(QtWidgets.QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{RETRO_GREEN}; color:{RETRO_TEXT}; border-top: 1px solid {RETRO_BORDER};")
        self.setSizeGripEnabled(False)

        left = QtWidgets.QLabel("NexGen-BBpro")
        right = QtWidgets.QLabel("JBARR 2025")
        right.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)

        container = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(container)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.addWidget(left)
        lay.addWidget(spacer)
        lay.addWidget(right)

        self.addPermanentWidget(container, 1)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Team Roster — Atlanta Warriors (Retro Mockup)")
        self.resize(930, 560)
        self._apply_global_palette()

        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)

        self.header = RetroHeader()
        self.table = RosterTable()
        v.addWidget(self.header)
        v.addWidget(self.table, 1)
        self.setCentralWidget(central)

        self._build_menus()

        self.statusbar = StatusFooter()
        self.setStatusBar(self.statusbar)

    # --- helpers -----------------------------------------------------------
    def _apply_global_palette(self):
        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(RETRO_GREEN))
        pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(RETRO_GREEN_TABLE))
        pal.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(RETRO_TEXT))
        pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(RETRO_BEIGE))
        pal.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#222"))
        self.setPalette(pal)
        self.setStyleSheet(
            f"QMainWindow {{ background:{RETRO_GREEN}; }}"
            f"QMenuBar {{ background:{RETRO_BEIGE}; color:#222; border-bottom:1px solid {RETRO_BORDER}; }}"
            f"QMenuBar::item:selected {{ background:#c7ab7a; }}"
            f"QMenu {{ background:{RETRO_BEIGE}; color:#222; }}"
        )

    def _build_menus(self):
        mb = self.menuBar()
        # Menus + placeholder actions (use partial to avoid late-binding lambdas)
        for menu_name in ("Main", "Association", "Team", "Do", "Show", "Help"):
            m = mb.addMenu(menu_name)
            act = QtGui.QAction("Placeholder Action", self)
            act.triggered.connect(
                partial(QtWidgets.QMessageBox.information, self, "Info", f"'{menu_name}' clicked")
            )
            m.addAction(act)

        # Add Exit action with a proper shortcut
        main_menu = mb.actions()[0].menu()
        main_menu.addSeparator()
        exit_action = QtGui.QAction("Exit", self)
        exit_action.setShortcut(QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Quit))
        exit_action.triggered.connect(self.close)
        main_menu.addAction(exit_action)

def build_and_show():
    app = QtWidgets.QApplication([])
    app.setApplicationDisplayName("Retro Roster Mockup")
    win = MainWindow()
    win.show()
    app.exec()

if __name__ == "__main__":
    build_and_show()
