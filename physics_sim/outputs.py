from __future__ import annotations

from typing import Dict, Any, List

from .engine import GameResult


def serialize_game_result(result: GameResult) -> Dict[str, Any]:
    """Return a dict compatible with the existing game stats writer."""

    return {
        "totals": result.totals,
        "pitch_log": result.pitch_log,
        "metadata": result.metadata,
    }
