from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
)


@dataclass
class Park:
    park_id: str
    name: str
    year: int


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_latest_parks(csv_path: Optional[Path] = None) -> List[Park]:
    root = _project_root()
    path = csv_path or (root / "data" / "parks" / "ParkConfig.csv")
    latest: Dict[str, Park] = {}
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            park_id = (row.get("parkID") or row.get("ParkID") or "").strip()
            name = (row.get("NAME") or row.get("Name") or "").strip()
            try:
                year = int(row.get("Year") or 0)
            except Exception:
                continue
            if not park_id or not name:
                continue
            p = Park(park_id=park_id, name=name, year=year)
            if park_id not in latest or year > latest[park_id].year:
                latest[park_id] = p
    return sorted(latest.values(), key=lambda p: p.name)


class ParkSelectorDialog(QDialog):
    """Allows choosing a ballpark from ParkConfig with a simple preview."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Stadium")
        self._parks = _load_latest_parks()
        self.selected_name: Optional[str] = None
        self.selected_park_id: Optional[str] = None

        root = QVBoxLayout(self)

        # Filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter by name…")
        self.filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_edit)
        root.addLayout(filter_row)

        # List + Preview
        main_row = QHBoxLayout()

        self.list = QListWidget()
        for p in self._parks:
            item = QListWidgetItem(f"{p.name} ({p.year})")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.list.addItem(item)
        self.list.currentItemChanged.connect(self._update_preview)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(320, 320)
        self.preview.setStyleSheet("background:#222; color:#ddd;")
        self.preview.setText("Select a park to preview")

        main_row.addWidget(self.list, 2)
        main_row.addWidget(self.preview, 3)
        root.addLayout(main_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_use = QPushButton("Use Stadium")
        self.btn_use.clicked.connect(self._accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_use)
        btn_row.addWidget(self.btn_cancel)
        root.addLayout(btn_row)

        # Default select first item
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _apply_filter(self, text: str) -> None:
        text = (text or "").lower()
        self.list.clear()
        for p in self._parks:
            label = f"{p.name} ({p.year})"
            if text in p.name.lower():
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.list.addItem(item)

    def _update_preview(self, item: Optional[QListWidgetItem]) -> None:
        if not item:
            return
        p: Park = item.data(Qt.ItemDataRole.UserRole)
        self.selected_name = p.name
        self.selected_park_id = p.park_id

        # Try to show a generated image if present
        img_path = _project_root() / "images" / "parks" / f"{p.park_id}_{p.year}.png"
        if not img_path.exists():
            # Generate on-demand using the generator module
            try:
                from scripts import generate_park_diagrams as gen
                # Load all parks, filter to this one, and render
                parks = gen.load_parks(_project_root() / "data" / "parks" / "ParkConfig.csv")
                parks = [r for r in parks if r.park_id == p.park_id and r.year == p.year]
                if parks:
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    gen.draw_diagram(parks[0], img_path)
            except Exception:
                pass

        if img_path.exists():
            pix = QPixmap(str(img_path))
            if not pix.isNull():
                self.preview.setPixmap(pix.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                return
        # Fallback text
        self.preview.setText(f"{p.name}\n(No preview available)")

    def resizeEvent(self, event):  # noqa: N802 - Qt signature
        # Keep image scaled to label
        super().resizeEvent(event)
        pix = self.preview.pixmap()
        if pix:
            self.preview.setPixmap(pix.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _accept(self) -> None:
        if self.selected_name:
            self.accept()

