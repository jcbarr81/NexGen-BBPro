from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
)
from PyQt6.QtGui import QIntValidator
from typing import Dict, List

from logic.playbalance_config import PlayBalanceConfig, _DEFAULTS


class PlayBalanceEditor(QDialog):
    """Dialog allowing administrators to tweak key PlayBalance values."""

    # Keys grouped by category for display in the tree widget.
    _CATEGORIES: Dict[str, List[str]] = {
        "Physics": [
            "speedBase",
            "swingSpeedBase",
            "averagePitchSpeed",
            "ballAirResistancePct",
        ],
        "AI": [
            "pitchRatVariationBase",
            "sureStrikeDist",
            "closeBallDist",
            "couldBeCaughtSlop",
        ],
        "Managerial": [
            "offManStealChancePct",
            "defManChargeChancePct",
            "defManPitchAroundToIBBPct",
            "doubleSwitchBase",
        ],
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Play Balance Editor")
        self.config = PlayBalanceConfig()
        self._editors: Dict[str, QLineEdit] = {}

        layout = QVBoxLayout()
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Key", "Value"])
        layout.addWidget(self.tree)

        validator = QIntValidator(self)

        for category, keys in self._CATEGORIES.items():
            cat_item = QTreeWidgetItem([category])
            self.tree.addTopLevelItem(cat_item)
            for key in keys:
                value = _DEFAULTS.get(key, 0)
                item = QTreeWidgetItem(cat_item, [key])
                editor = QLineEdit(str(value))
                editor.setValidator(validator)
                self.tree.setItemWidget(item, 1, editor)
                self._editors[key] = editor
            cat_item.setExpanded(True)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        reset_btn = QPushButton("Reset to Defaults")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.save)
        reset_btn.clicked.connect(self.reset_defaults)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def save(self) -> None:
        """Persist edited values to overrides."""
        for key, editor in self._editors.items():
            text = editor.text().strip()
            if not text:
                continue
            value = int(editor.text())
            self.config.values[key] = value
        self.config.save_overrides()
        self.accept()

    def reset_defaults(self) -> None:
        """Restore defaults and update the UI."""
        self.config.reset()
        for key, editor in self._editors.items():
            editor.setText(str(_DEFAULTS.get(key, 0)))

