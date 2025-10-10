"""League lifecycle actions for the admin dashboard."""
from __future__ import annotations

import csv
import json
import shutil
from typing import Callable, Iterable, Optional, Tuple

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QInputDialog,
    QMessageBox,
    QWidget,
)

from playbalance.league_creator import create_league
from playbalance.season_manager import SeasonManager, SeasonPhase

from ui.team_entry_dialog import TeamEntryDialog
from ui.window_utils import ensure_on_top
from utils.news_logger import log_news_event
from utils.path_utils import get_base_dir
from utils.player_loader import load_players_from_csv

from ..context import DashboardContext

AfterCallback = Optional[Callable[[], None]]


def _schedule(callback: Callable[[], None]) -> None:
    QTimer.singleShot(0, callback)


def create_league_action(
    context: DashboardContext,
    parent: Optional[QWidget] = None,
    refresh_callbacks: Iterable[Callable[[], None]] | None = None,
) -> None:
    """Launch the guided dialog flow for creating a new league."""

    if parent is None:
        return

    confirm = QMessageBox.question(
        parent,
        "Overwrite Existing League?",
        (
            "Creating a new league will overwrite the current league and "
            "teams. Continue?"
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if confirm != QMessageBox.StandardButton.Yes:
        return

    league_name, ok = QInputDialog.getText(parent, "League Name", "Enter league name:")
    if not ok or not league_name:
        return
    league_name = league_name.strip()

    div_text, ok = QInputDialog.getText(
        parent,
        "Divisions",
        "Enter division names separated by commas:",
    )
    if not ok or not div_text:
        return

    divisions = [d.strip() for d in div_text.split(",") if d.strip()]
    if not divisions:
        return

    teams_per_div, ok = QInputDialog.getInt(
        parent,
        "Teams",
        "Teams per division:",
        2,
        1,
        20,
    )
    if not ok:
        return

    dialog = TeamEntryDialog(divisions, teams_per_div, parent)
    ensure_on_top(dialog)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    structure = dialog.get_structure()
    data_dir = get_base_dir() / "data"
    try:
        create_league(str(data_dir), structure, league_name)
    except OSError as exc:
        QMessageBox.critical(parent, "Error", f"Failed to purge existing league: {exc}")
        return

    QMessageBox.information(parent, "League Created", "New league generated.")
    for callback in refresh_callbacks or ():
        try:
            callback()
        except Exception:
            pass



def reset_season_to_opening_day(
    context: DashboardContext,
    parent: Optional[QWidget] = None,
    after_reset: AfterCallback = None,
) -> None:
    """Reset season progress, standings, and supporting data asynchronously."""

    if parent is None:
        return

    confirm = QMessageBox.question(
        parent,
        "Reset to Opening Day",
        (
            "This will clear all regular-season results and standings, "
            "and rewind the season to Opening Day. Continue?"
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if confirm != QMessageBox.StandardButton.Yes:
        return

    data_root = get_base_dir() / "data"
    sched = data_root / "schedule.csv"
    purge_box = (
        QMessageBox.question(
            parent,
            "Purge Boxscores?",
            "Also delete saved season boxscores (data/boxscores/season)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        == QMessageBox.StandardButton.Yes
    )

    if not sched.exists():
        QMessageBox.warning(
            parent,
            "No Schedule",
            "Cannot reset: schedule.csv not found. Generate a schedule first.",
        )
        return

    if context.show_toast:
        context.show_toast("info", "Resetting league in background...")

    def worker() -> Tuple[str, str]:
        progress = data_root / "season_progress.json"
        standings = data_root / "standings.json"
        stats_file = data_root / "season_stats.json"
        history_dir = data_root / "season_history"
        notes: list[str] = []

        try:
            rows: list[dict[str, str]] = []
            with sched.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for record in reader:
                    record = dict(record)
                    record["result"] = ""
                    record["played"] = ""
                    record["boxscore"] = ""
                    rows.append(record)
        except Exception as exc:
            raise RuntimeError(f"Failed reading schedule: {exc}") from exc

        try:
            fieldnames = ["date", "home", "away", "result", "played", "boxscore"]
            with sched.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for record in rows:
                    writer.writerow({
                        "date": record.get("date", ""),
                        "home": record.get("home", ""),
                        "away": record.get("away", ""),
                        "result": record.get("result", ""),
                        "played": record.get("played", ""),
                        "boxscore": record.get("boxscore", ""),
                    })
        except Exception as exc:
            raise RuntimeError(f"Failed rewriting schedule: {exc}") from exc

        first_year: Optional[int] = None
        try:
            if rows:
                first = rows[0]
                if first.get("date"):
                    first_year = int(str(first["date"]).split("-")[0])
        except Exception:
            first_year = None

        try:
            data = {
                "preseason_done": {
                    "free_agency": True,
                    "training_camp": True,
                    "schedule": True,
                },
                "sim_index": 0,
                "playoffs_done": False,
            }
            if progress.exists():
                try:
                    current = json.loads(progress.read_text(encoding="utf-8"))
                    completed = set(current.get("draft_completed_years", []))
                    if first_year is not None and first_year in completed:
                        completed.discard(first_year)
                    if completed:
                        data["draft_completed_years"] = sorted(completed)
                except Exception:
                    pass
            progress.parent.mkdir(parents=True, exist_ok=True)
            progress.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"Failed resetting progress: {exc}") from exc

        try:
            standings.parent.mkdir(parents=True, exist_ok=True)
            standings.write_text("{}", encoding="utf-8")
        except Exception:
            pass

        try:
            stats_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                if history_dir.exists():
                    shutil.rmtree(history_dir)
            except Exception:
                pass
            try:
                lock = stats_file.with_suffix(stats_file.suffix + ".lock")
                if lock.exists():
                    lock.unlink()
            except Exception:
                pass
            if stats_file.exists():
                try:
                    stats_file.unlink()
                except Exception:
                    pass
            stats_file.write_text(
                '{"players": {}, "teams": {}, "history": []}',
                encoding="utf-8",
            )
        except Exception:
            pass

        try:
            if first_year is not None:
                draft_files = [
                    f"draft_pool_{first_year}.json",
                    f"draft_pool_{first_year}.csv",
                    f"draft_state_{first_year}.json",
                    f"draft_results_{first_year}.csv",
                ]
                for name in draft_files:
                    target = data_root / name
                    try:
                        lock = target.with_suffix(target.suffix + ".lock")
                        if lock.exists():
                            lock.unlink()
                    except Exception:
                        pass
                    if target.exists():
                        try:
                            target.unlink()
                        except Exception:
                            pass
        except Exception:
            pass

        try:
            playoff_candidates = [data_root / "playoffs.json"]
            if first_year is not None:
                playoff_candidates.append(data_root / f"playoffs_{first_year}.json")
            try:
                playoff_candidates.extend(data_root.glob("playoffs_*.json"))
            except Exception:
                pass
            for candidate in playoff_candidates:
                try:
                    if candidate.exists():
                        bak = candidate.with_suffix(candidate.suffix + ".bak")
                        lock = candidate.with_suffix(candidate.suffix + ".lock")
                        if lock.exists():
                            lock.unlink()
                        if bak.exists():
                            bak.unlink()
                        candidate.unlink()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            manager = SeasonManager()
            manager.phase = SeasonPhase.REGULAR_SEASON
            manager.save()
            try:
                manager.finalize_rosters()
            except Exception:
                pass
            try:
                load_players_from_csv.cache_clear()  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception as exc:
            notes.append(f"State updated, but failed setting phase: {exc}")

        try:
            log_news_event("League reset to Opening Day")
        except Exception:
            pass

        if purge_box:
            try:
                box_dir = data_root / "boxscores" / "season"
                if box_dir.exists():
                    shutil.rmtree(box_dir)
                log_news_event("Purged saved season boxscores")
            except Exception as exc:
                notes.append(f"Boxscore purge failed: {exc}")

        message = "League reset to Opening Day."
        if purge_box:
            message += " Season boxscores purged."
        if notes:
            message += " " + " ".join(notes)
        return "success", message

    def handle_result(result_future) -> None:
        try:
            kind, message = result_future.result()
        except Exception as exc:
            kind, message = "error", str(exc)

        def finish() -> None:
            if parent is not None:
                if kind == "success":
                    QMessageBox.information(parent, "Reset Complete", message)
                else:
                    QMessageBox.warning(parent, "Reset Failed", message)
            if context.show_toast:
                toast_kind = "success" if kind == "success" else "error"
                context.show_toast(toast_kind, message)
            if kind == "success" and after_reset is not None:
                try:
                    after_reset()
                except Exception:
                    pass

        _schedule(finish)

    future = context.run_async(worker)
    if hasattr(future, "add_done_callback"):
        future.add_done_callback(handle_result)
        if context.register_cleanup and hasattr(future, "cancel"):
            context.register_cleanup(lambda fut=future: fut.cancel())
    else:
        try:
            result = worker()
        except Exception as exc:
            result = ("error", str(exc))
        class _Immediate:
            def __init__(self, value):
                self._value = value
            def result(self):
                return self._value
        handle_result(_Immediate(result))


__all__ = ["create_league_action", "reset_season_to_opening_day"]

