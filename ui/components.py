"""Reusable UI components for consistent styling."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QToolButton,
    QFrame,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QWidget,
    QGridLayout,
)


class NavButton(QToolButton):
    """Navigation button used in sidebars."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("NavButton")
        # Emoji icons keep dependencies light; swap for SVGs if you prefer
        self.setText(text)  # e.g., "⚾  Dashboard"
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class Card(QFrame):
    """Framed container with standard padding and layout."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(18, 18, 18, 18)
        self.layout().setSpacing(10)


def section_title(text: str) -> QLabel:
    """Create a standardized section header label."""

    label = QLabel(text)
    label.setObjectName("SectionTitle")
    return label


def spacer(h: int = 1, v: int = 1) -> QSpacerItem:
    """Return a flexible spacer item for layouts."""

    return QSpacerItem(
        h,
        v,
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )


def metric_widget(title: str, value: str, *, highlight: bool = False) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    title_label = QLabel(title.upper())
    title_label.setObjectName('MetricLabel')
    value_label = QLabel(value)
    value_label.setObjectName('MetricValue')
    if highlight:
        value_label.setProperty('highlight', True)

    layout.addWidget(title_label)
    layout.addWidget(value_label)
    layout.addStretch()
    return container


def build_metric_row(pairs: list[tuple[str, str]], *, columns: int = 4) -> QWidget:
    wrapper = QWidget()
    grid = QGridLayout(wrapper)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(18)
    for idx, (title, value) in enumerate(pairs):
        row = idx // columns
        col = idx % columns
        grid.addWidget(metric_widget(title, value), row, col)
    return wrapper
