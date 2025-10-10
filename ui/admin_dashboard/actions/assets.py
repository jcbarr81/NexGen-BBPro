"""Asset generation actions for the admin dashboard."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget, QProgressDialog

from utils.avatar_generator import generate_player_avatars
from utils.logo_generator import generate_team_logos

from ..context import DashboardContext


def _schedule(callback) -> None:
    QTimer.singleShot(0, callback)


def generate_team_logos_action(
    context: DashboardContext,
    parent: Optional[QWidget] = None,
) -> None:
    """Generate team logos on a background worker."""

    if context.show_toast:
        context.show_toast("info", "Generating team logos in background...")

    progress_state: dict[str, object] = {
        "dialog": None,
        "done": 0,
        "total": 0,
        "status": "openai",
    }

    if parent is not None:
        dialog = QProgressDialog("Generating team logos...", None, 0, 1, parent)
        dialog.setWindowTitle("Generating Team Logos")
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(True)
        dialog.setAutoReset(True)
        dialog.setValue(0)
        dialog.show()
        progress_state["dialog"] = dialog

    def update_label() -> None:
        dialog = progress_state.get("dialog")
        if dialog is None:
            return
        done = int(progress_state.get("done", 0) or 0)
        total = int(progress_state.get("total", 0) or 0)
        status = progress_state.get("status", "openai")
        label = "Generating team logos..."
        if total:
            label = f"Generating team logos... ({done}/{total})"
        if status == "auto_logo":
            label = f"{label}\nLegacy auto-logo generator in use"
        dialog.setLabelText(label)

    def close_progress() -> None:
        dialog = progress_state.get("dialog")
        if dialog is not None:
            dialog.reset()
            dialog.close()
        progress_state["dialog"] = None

    def progress_cb(done: int, total: int) -> None:
        if progress_state.get("dialog") is None:
            return

        def update() -> None:
            dialog = progress_state.get("dialog")
            if dialog is None:
                return
            progress_state["done"] = done
            progress_state["total"] = total
            maximum = total if total > 0 else 1
            if dialog.maximum() != maximum:
                dialog.setMaximum(maximum)
            value = max(0, min(done, maximum))
            dialog.setValue(value)
            update_label()

        _schedule(update)

    def status_cb(mode: str) -> None:
        progress_state["status"] = mode

        def update() -> None:
            update_label()

        _schedule(update)

    def worker() -> None:
        try:
            out_dir = generate_team_logos(
                progress_callback=progress_cb,
                status_callback=status_cb,
            )
        except Exception as exc:
            def fail() -> None:
                close_progress()
                if parent is not None:
                    QMessageBox.warning(parent, "Logo Generation Failed", str(exc))
                if context.show_toast:
                    context.show_toast("error", f"Logo generation failed: {exc}")

            _schedule(fail)
        else:
            def success() -> None:
                close_progress()
                note = None
                if progress_state.get("status") == "auto_logo":
                    note = (
                        "OpenAI client is not configured, so the legacy auto-logo "
                        "generator was used for these logos."
                    )
                lines = [f"Team logos saved to {out_dir}"]
                if note:
                    lines.append(note)
                message = "\n\n".join(lines)
                if parent is not None:
                    QMessageBox.information(parent, "Logos Generated", message)
                if context.show_toast:
                    toast_msg = "Team logos generated."
                    if note:
                        toast_msg = "Team logos generated using legacy auto-logo fallback."
                    context.show_toast("success", toast_msg)

            _schedule(success)

    context.run_async(worker)


def generate_player_avatars_action(
    context: DashboardContext,
    parent: Optional[QWidget] = None,
) -> None:
    """Generate player avatars asynchronously."""

    initial = False
    if parent is not None:
        initial = (
            QMessageBox.question(
                parent,
                "Initial Creation",
                "Is this the initial creation of player avatars?\n"
                "Yes will remove existing avatars (except Template).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    if context.show_toast:
        context.show_toast("info", "Generating player avatars in background...")

    def worker() -> None:
        try:
            out_dir = generate_player_avatars(
                progress_callback=None,
                initial_creation=initial,
            )
        except Exception as exc:
            def fail() -> None:
                if parent is not None:
                    QMessageBox.warning(parent, "Avatar Generation Failed", str(exc))
                if context.show_toast:
                    context.show_toast("error", f"Avatar generation failed: {exc}")

            _schedule(fail)
        else:
            def success() -> None:
                if parent is not None:
                    QMessageBox.information(parent, "Avatars Generated", f"Player avatars saved to {out_dir}")
                if context.show_toast:
                    context.show_toast("success", "Player avatars generated.")

            _schedule(success)

    context.run_async(worker)


__all__ = [
    "generate_player_avatars_action",
    "generate_team_logos_action",
]
