"""Utilities for maintaining season standings metrics."""
from __future__ import annotations

from typing import Dict, List

__all__ = ["default_record", "normalize_record", "update_record"]


def default_record() -> Dict[str, object]:
    """Return a fresh standings record with zeroed statistics."""

    return {
        "wins": 0,
        "losses": 0,
        "runs_for": 0,
        "runs_against": 0,
        "one_run_wins": 0,
        "one_run_losses": 0,
        "extra_innings_wins": 0,
        "extra_innings_losses": 0,
        "home_wins": 0,
        "home_losses": 0,
        "road_wins": 0,
        "road_losses": 0,
        "vs_rhp_wins": 0,
        "vs_rhp_losses": 0,
        "vs_lhp_wins": 0,
        "vs_lhp_losses": 0,
        "division_wins": 0,
        "division_losses": 0,
        "non_division_wins": 0,
        "non_division_losses": 0,
        "last10": [],
        "streak": {"result": None, "length": 0},
    }


def _coerce_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_record(data: Dict[str, object] | None) -> Dict[str, object]:
    """Return ``data`` merged with default keys and normalized values."""

    record = default_record()
    if not data:
        return record

    for key in (k for k in record if k not in {"last10", "streak"}):
        record[key] = _coerce_int(data.get(key), record[key])

    raw_last10 = data.get("last10", [])
    if isinstance(raw_last10, list):
        normalized = []
        for entry in raw_last10[-10:]:
            text = str(entry).strip().upper()
            normalized.append("W" if text.startswith("W") else "L" if text.startswith("L") else "")
        record["last10"] = [entry for entry in normalized if entry in {"W", "L"}]
    else:
        record["last10"] = []

    streak_data = data.get("streak", {})
    if isinstance(streak_data, dict):
        result = streak_data.get("result")
        if result not in {"W", "L"}:
            result = None
        length = _coerce_int(streak_data.get("length"), 0)
        record["streak"] = {"result": result, "length": max(length, 0)}
    else:
        record["streak"] = {"result": None, "length": 0}

    return record


def update_record(
    record: Dict[str, object],
    *,
    won: bool,
    runs_for: int,
    runs_against: int,
    home: bool,
    opponent_hand: str,
    division_game: bool,
    one_run: bool,
    extra_innings: bool,
) -> None:
    """Update ``record`` for a completed game."""

    outcome = "W" if won else "L"
    record["wins"] = _coerce_int(record.get("wins"))
    record["losses"] = _coerce_int(record.get("losses"))
    if won:
        record["wins"] += 1
    else:
        record["losses"] += 1
    record["runs_for"] = _coerce_int(record.get("runs_for")) + runs_for
    record["runs_against"] = _coerce_int(record.get("runs_against")) + runs_against

    if one_run:
        key = "one_run_wins" if won else "one_run_losses"
        record[key] = _coerce_int(record.get(key)) + 1

    if extra_innings:
        key = "extra_innings_wins" if won else "extra_innings_losses"
        record[key] = _coerce_int(record.get(key)) + 1

    if home:
        key = "home_wins" if won else "home_losses"
    else:
        key = "road_wins" if won else "road_losses"
    record[key] = _coerce_int(record.get(key)) + 1

    hand = (opponent_hand or "").upper()
    if hand.startswith("L"):
        key = "vs_lhp_wins" if won else "vs_lhp_losses"
    else:
        key = "vs_rhp_wins" if won else "vs_rhp_losses"
    record[key] = _coerce_int(record.get(key)) + 1

    if division_game:
        key = "division_wins" if won else "division_losses"
    else:
        key = "non_division_wins" if won else "non_division_losses"
    record[key] = _coerce_int(record.get(key)) + 1

    record.setdefault("last10", [])
    record["last10"].append(outcome)
    record["last10"] = record["last10"][-10:]

    streak = record.setdefault("streak", {"result": None, "length": 0})
    if streak.get("result") == outcome:
        streak["length"] = _coerce_int(streak.get("length"), 0) + 1
    else:
        streak["result"] = outcome
        streak["length"] = 1

