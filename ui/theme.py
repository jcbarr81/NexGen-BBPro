from __future__ import annotations

from typing import Optional
from PyQt6.QtWidgets import QApplication, QStatusBar

LIGHT_QSS = """
/* App */
QWidget {
    background: #f7f8fb;
    color: #1a1a1a;
    font-family: 'Segoe UI', 'Noto Sans', Arial;
    font-size: 14px;
    font-weight: 500;
}

/* Sidebar (dugout) */
#Sidebar {
    background: #0f2545; /* deep navy */
    border: none;
}
#Sidebar QLabel {
    color: #f1f5ff;
    font-weight: 600;
    padding: 8px 10px;
    letter-spacing: .5px;
}
#NavButton {
    color: #e7efff;
    background: transparent;
    padding: 10px 14px;
    margin: 4px 8px;
    border-radius: 10px;
    text-align: left;
}
#NavButton:hover { background: #1b3b6b; }
#NavButton:checked {
    background: #1b4d89;
    border: 1px solid #2b66b8;
    color: white;
}

/* Header (scoreboard strip) */
#Header {
    background: white;
    border-bottom: 1px solid #e6e9f2;
}
#Title {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: .5px;
}
#Scoreboard {
    background: #0f2545;
    color: #f6f8ff;
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 700;
}

/* Cards and content */
QFrame#Card {
    background: white;
    border: 1px solid #e9edf5;
    border-radius: 14px;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #0f2545;
}

/* Buttons */
QPushButton {
    background: #e0e6ef;
    color: #0f2545;
    border: 1px solid #b5bdc9;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton:hover { background: #d3dae5; }
QPushButton:pressed { background: #c2c9d4; }

QPushButton#Primary {
    background: #1b4d89;  /* primary blue */
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#Primary:hover { background: #205aa0; }
QPushButton#Primary:pressed { background: #17487a; }

QPushButton#Success {
    background: #2f9e44;  /* "Play ball" green */
    color: white;
    border: none;
    padding: 12px 18px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#Success:hover { background: #27903c; }
QPushButton#Success:pressed { background: #237f35; }

QStatusBar { background: #ffffff; border-top: 1px solid #e6e9f2; }
"""

DARK_QSS = """
QWidget {
    background: #0f1623;
    color: #e6ecfa;
    font-family: 'Segoe UI', 'Noto Sans', Arial;
    font-size: 14px;
    font-weight: 500;
}
#Sidebar {
    background: #0b1222;
}
#Sidebar QLabel { color: #dbe6ff; }
#NavButton {
    color: #cfe0ff;
    background: transparent;
    padding: 10px 14px;
    margin: 4px 8px;
    border-radius: 10px;
}
#NavButton:hover { background: #132645; }
#NavButton:checked {
    background: #19345f;
    border: 1px solid #2a4c8e;
    color: white;
}
#Header {
    background: #111a2b;
    border-bottom: 1px solid #1b2943;
}
#Title { color: #eaf1ff; }
#Scoreboard {
    background: #0b1222;
    color: #eaf1ff;
    border: 1px solid #1b2943;
    border-radius: 10px;
    padding: 6px 12px;
    font-weight: 700;
}
QFrame#Card {
    background: #121b2d;
    border: 1px solid #1b2943;
    border-radius: 14px;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #e6ecfa;
}
QPushButton {
    background: #1b2e45;
    color: #e6ecfa;
    border: 1px solid #2a4c8e;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton:hover { background: #243a57; }
QPushButton:pressed { background: #1a273a; }
QPushButton#Primary {
    background: #1b4d89;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#Primary:hover { background: #205aa0; }
QPushButton#Primary:pressed { background: #17487a; }
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
QStatusBar { background: #0f1623; border-top: 1px solid #1b2943; }
"""

def _toggle_theme(status_bar: Optional[QStatusBar] = None) -> None:
    """Toggle between light and dark themes."""
    app = QApplication.instance()
    if app is None:
        return
    is_dark = "0f1623" in app.styleSheet()
    app.setStyleSheet(LIGHT_QSS if is_dark else DARK_QSS)
    if status_bar is not None:
        status_bar.showMessage("Light theme" if is_dark else "Dark theme")

