"""Reusable UI components for consistent styling."""

from typing import Any

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


def _call_if_exists(obj: Any, method: str, *args: Any, **kwargs: Any) -> None:
    """Invoke ``method`` on ``obj`` when available."""

    func = getattr(obj, method, None)
    if callable(func):
        try:
            func(*args, **kwargs)
        except Exception:
            pass


class NavButton(QToolButton):
    """Navigation button used in sidebars."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        _call_if_exists(self, "setObjectName", "NavButton")
        # Emoji icons keep dependencies light; swap for SVGs if you prefer
        _call_if_exists(self, "setText", text)  # e.g., "⚾  Dashboard"
        _call_if_exists(self, "setCheckable", True)
        style = getattr(Qt.ToolButtonStyle, "ToolButtonTextOnly", None)
        if style is not None:
            _call_if_exists(self, "setToolButtonStyle", style)
        policy_enum = getattr(QSizePolicy, "Policy", None)
        h_policy = getattr(policy_enum, "Expanding", None) if policy_enum else None
        v_policy = getattr(policy_enum, "Fixed", None) if policy_enum else None
        if h_policy is not None and v_policy is not None:
            _call_if_exists(self, "setSizePolicy", h_policy, v_policy)


class Card(QFrame):
    """Framed container with standard padding and layout."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        _call_if_exists(self, "setObjectName", "Card")
        policy_enum = getattr(QSizePolicy, "Policy", None)
        h_policy = getattr(policy_enum, "Expanding", None) if policy_enum else None
        v_policy = getattr(policy_enum, "Minimum", None) if policy_enum else None
        if h_policy is not None and v_policy is not None:
            _call_if_exists(self, "setSizePolicy", h_policy, v_policy)
        shape_enum = getattr(QFrame, "Shape", None)
        frame_shape = getattr(shape_enum, "StyledPanel", None)
        if frame_shape is not None:
            _call_if_exists(self, "setFrameShape", frame_shape)
        layout = QVBoxLayout()
        self._fallback_layout = layout
        _call_if_exists(self, "setLayout", layout)
        _call_if_exists(layout, "setContentsMargins", 18, 18, 18, 18)
        _call_if_exists(layout, "setSpacing", 10)

    def layout(self):  # type: ignore[override]
        """Return the active layout, falling back to the stored layout for stubs."""

        base_layout = None
        try:
            base_method = getattr(super(), "layout", None)
            if callable(base_method):
                candidate = base_method()
                if candidate is not None and candidate is not self:
                    base_layout = candidate
        except Exception:
            base_layout = None
        return base_layout or getattr(self, "_fallback_layout", None)


def ensure_layout(widget: Any) -> Any:
    """Return a layout object for ``widget`` that supports layout operations."""

    layout_attr = getattr(widget, "layout", None)
    if callable(layout_attr):
        try:
            candidate = layout_attr()
            if candidate is not None and candidate is not widget:
                return candidate
        except TypeError:
            pass
    fallback = getattr(widget, "_fallback_layout", None)
    return fallback or layout_attr or widget


def section_title(text: str) -> QLabel:
    """Create a standardized section header label."""

    label = QLabel(text)
    _call_if_exists(label, "setObjectName", "SectionTitle")
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
    _call_if_exists(layout, "setContentsMargins", 0, 0, 0, 0)
    _call_if_exists(layout, "setSpacing", 4)

    title_label = QLabel(title.upper())
    _call_if_exists(title_label, "setObjectName", "MetricLabel")
    value_label = QLabel(value)
    _call_if_exists(value_label, "setObjectName", "MetricValue")
    if highlight:
        _call_if_exists(value_label, "setProperty", "highlight", True)

    _call_if_exists(layout, "addWidget", title_label)
    _call_if_exists(layout, "addWidget", value_label)
    _call_if_exists(layout, "addStretch")
    return container


def build_metric_row(pairs: list[tuple[str, str]], *, columns: int = 4) -> QWidget:
    wrapper = QWidget()
    grid = QGridLayout(wrapper)
    _call_if_exists(grid, "setContentsMargins", 0, 0, 0, 0)
    _call_if_exists(grid, "setSpacing", 18)
    for idx, (title, value) in enumerate(pairs):
        row = idx // columns
        col = idx % columns
        _call_if_exists(grid, "addWidget", metric_widget(title, value), row, col)
    return wrapper
