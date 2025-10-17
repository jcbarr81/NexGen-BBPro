from __future__ import annotations

"""Attach a floating version badge to selected top-level Qt windows."""

from typing import Any
import weakref

try:  # pragma: no cover - import guard for headless test stubs
    from PyQt6.QtCore import QEvent, QObject, Qt
    from PyQt6.QtWidgets import QApplication, QLabel, QWidget
except Exception:  # pragma: no cover - minimal fallback used in tests
    def install_version_badge(app: Any) -> None:
        """No-op when PyQt6 widgets are unavailable."""

        return None

    def enable_version_badge(widget: Any) -> None:
        """Fallback helper when Qt widgets are stubbed out."""

        return None

    __all__ = ["install_version_badge", "enable_version_badge"]
else:
    from utils.version import get_version

    _BADGE_MARGIN = 16
    _BADGE_PROP = "nexgen_version_badge"
    _MANAGER_PROP = "_nexgen_version_badge_manager"

    class _WindowBadge(QObject):
        """Manage a per-window badge label that tracks resize events."""

        def __init__(self, window: QWidget) -> None:
            super().__init__(window)
            self._window = window
            self._label = QLabel(window)
            self._label.setObjectName("VersionBadge")
            self._label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            self._label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._window.installEventFilter(self)
            self._refresh()

        def eventFilter(self, watched: QObject, event: QEvent) -> bool:
            if watched is self._window and event.type() in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
            ):
                self._refresh()
            return super().eventFilter(watched, event)

        def _refresh(self) -> None:
            if not self._window.isVisible():
                return
            version = get_version()
            prefix = "v" if not version.lower().startswith("v") else ""
            self._label.setText(f"{prefix}{version}")
            self._label.adjustSize()
            width = self._window.width()
            height = self._window.height()
            label_width = self._label.width()
            label_height = self._label.height()
            x = max(_BADGE_MARGIN, width - label_width - _BADGE_MARGIN)
            y = max(_BADGE_MARGIN, height - label_height - _BADGE_MARGIN)
            self._label.move(x, y)
            self._label.show()
            try:
                self._label.raise_()
            except Exception:
                pass

    class _BadgeInstaller(QObject):
        """Application-level event filter that injects badges onto windows."""

        def __init__(self, app: QApplication) -> None:
            super().__init__(app)
            self._badges: "weakref.WeakKeyDictionary[QWidget, _WindowBadge]" = (
                weakref.WeakKeyDictionary()
            )
            self._app = app
            app.installEventFilter(self)

        def eventFilter(self, watched: QObject, event: QEvent) -> bool:
            if isinstance(watched, QWidget) and watched.isWindow():
                if bool(watched.property(_BADGE_PROP)):
                    if event.type() == QEvent.Type.Show:
                        self._ensure_badge(watched)
                    elif event.type() == QEvent.Type.Hide:
                        badge = self._badges.get(watched)
                        if badge is not None:
                            badge._label.hide()  # type: ignore[attr-defined]
            return super().eventFilter(watched, event)

        def request_badge(self, window: QWidget) -> None:
            if bool(window.property(_BADGE_PROP)):
                self._ensure_badge(window)

        def _ensure_badge(self, window: QWidget) -> None:
            if window not in self._badges:
                self._badges[window] = _WindowBadge(window)

    def install_version_badge(app: QApplication) -> None:
        """Install the global badge manager for *app* once per process."""

        if app.property("_nexgen_version_badge_installed"):
            return
        manager = _BadgeInstaller(app)
        app.setProperty("_nexgen_version_badge_installed", True)
        app.setProperty(_MANAGER_PROP, manager)

    def enable_version_badge(widget: QWidget) -> None:
        """Mark *widget* for version display and attach a badge when possible."""

        widget.setProperty(_BADGE_PROP, True)
        app = QApplication.instance()
        if app is None:
            return
        install_version_badge(app)
        manager = app.property(_MANAGER_PROP)
        if isinstance(manager, _BadgeInstaller):
            manager.request_badge(widget)

    __all__ = ["install_version_badge", "enable_version_badge"]
