from __future__ import annotations

from typing import Optional
from PyQt6.QtWidgets import QApplication, QStatusBar

LIGHT_QSS = """
/* App */
QWidget {
    background: #fffdf0;
    color: #462d0d;
    font-family: 'Segoe UI', 'Noto Sans', Arial;
    font-size: 14px;
    font-weight: 500;
}

/* Sidebar (dugout) */
#Sidebar {
    background: #462d0d; /* deep brown */
    border: none;
}
#Sidebar QLabel {
    color: #fffdf0;
    font-weight: 600;
    padding: 8px 10px;
    letter-spacing: .5px;
}
#NavButton {
    color: #fffdf0;
    background: transparent;
    padding: 10px 14px;
    margin: 4px 8px;
    border-radius: 10px;
    text-align: left;
}
#NavButton:hover { background: #604d33; }
#NavButton:checked {
    background: #604d33;
    border: 1px solid #968d7d;
    color: #fffdf0;
}

/* Header (scoreboard strip) */
#Header {
    background: #fffdf0;
    border-bottom: 1px solid #968d7d;
}
#Title {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: .5px;
    color: #462d0d;
}
#Scoreboard {
    background: #604d33;
    color: #fffdf0;
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 700;
}

/* Cards and content */
QFrame#Card {
    background: #fffdf0;
    border: 1px solid #968d7d;
    border-radius: 14px;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #462d0d;
}
QLabel#MetricLabel {
    font-size: 12px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #6f5c42;
}
QLabel#MetricValue {
    font-size: 24px;
    font-weight: 800;
    color: #462d0d;
}
QLabel#MetricValue[highlight="true"] { color: #c3521f; }

/* Buttons */
QPushButton {
    background: #968d7d;
    color: #fffdf0;
    border: 1px solid #604d33;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton:hover { background: #a59c8c; }
QPushButton:pressed { background: #857d6f; }

QPushButton#Primary {
    background: #604d33;
    color: #fffdf0;
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#Primary:hover { background: #6f5c42; }
QPushButton#Primary:pressed { background: #513e24; }

QPushButton#Success {
    background: #2f9e44;
    color: white;
    border: none;
    padding: 12px 18px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#Success:hover { background: #27903c; }
QPushButton#Success:pressed { background: #237f35; }

/* Destructive actions */
QPushButton#Danger {
    background: #a61e1e;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 700;
}
QPushButton#Danger:hover { background: #b32d2d; }
QPushButton#Danger:pressed { background: #8f1a1a; }

QStatusBar { background: #fffdf0; border-top: 1px solid #968d7d; }
"""

DARK_QSS = """
QWidget {
    background: #1e1207;
    color: #fffdf0;
    font-family: 'Segoe UI', 'Noto Sans', Arial;
    font-size: 14px;
    font-weight: 500;
}
#Sidebar {
    background: #160e04;
}
#Sidebar QLabel { color: #fffdf0; }
#NavButton {
    color: #fffdf0;
    background: transparent;
    padding: 10px 14px;
    margin: 4px 8px;
    border-radius: 10px;
}
#NavButton:hover { background: #2c1b0a; }
#NavButton:checked {
    background: #3b2810;
    border: 1px solid #604d33;
    color: #fffdf0;
}
#Header {
    background: #221508;
    border-bottom: 1px solid #3b2810;
}
#Title { color: #fffdf0; }
#Scoreboard {
    background: #160e04;
    color: #fffdf0;
    border: 1px solid #3b2810;
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 700;
}
QFrame#Card {
    background: #221508;
    border: 1px solid #3b2810;
    border-radius: 14px;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #fffdf0;
}
QLabel#MetricLabel {
    font-size: 12px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #a59c8c;
}
QLabel#MetricValue {
    font-size: 24px;
    font-weight: 800;
    color: #fffdf0;
}
QLabel#MetricValue[highlight="true"] { color: #e67700; }
QPushButton {
    background: #3b2810;
    color: #fffdf0;
    border: 1px solid #604d33;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton:hover { background: #4f3c29; }
QPushButton:pressed { background: #2c1b0a; }
QPushButton#Primary {
    background: #604d33;
    color: #fffdf0;
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#Primary:hover { background: #6f5c42; }
QPushButton#Primary:pressed { background: #513e24; }
QPushButton#Success {
    background: #2f9e44;
    color: white;
    border: none;
    padding: 12px 18px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#Success:hover { background: #27903c; }
QPushButton#Success:pressed { background: #237f35; }
/* Destructive actions */
QPushButton#Danger {
    background: #8f1a1a;
    color: white;
    border: 1px solid #b32d2d;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 700;
}
QPushButton#Danger:hover { background: #a61e1e; }
QPushButton#Danger:pressed { background: #701313; }
QStatusBar { background: #1e1207; border-top: 1px solid #3b2810; }
"""

def _toggle_theme(status_bar: Optional[QStatusBar] = None) -> None:
    """Toggle between light and dark themes."""
    app = QApplication.instance()
    if app is None:
        return
    is_dark = "1e1207" in app.styleSheet()
    app.setStyleSheet(LIGHT_QSS if is_dark else DARK_QSS)
    if status_bar is not None:
        status_bar.showMessage("Light theme" if is_dark else "Dark theme")

