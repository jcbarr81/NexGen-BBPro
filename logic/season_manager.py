from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from utils.path_utils import get_base_dir


class SeasonPhase(Enum):
    """Enumeration of the different phases of a season."""

    PRESEASON = "PRESEASON"
    REGULAR_SEASON = "REGULAR_SEASON"
    PLAYOFFS = "PLAYOFFS"
    OFFSEASON = "OFFSEASON"

    def next(self) -> "SeasonPhase":
        """Return the next phase, cycling back to ``PRESEASON``."""
        members = list(type(self))
        index = members.index(self)
        return members[(index + 1) % len(members)]


class SeasonManager:
    """Manage the current season phase and persist it to disk."""

    def __init__(self, path: str | Path | None = None) -> None:
        base_dir = get_base_dir()
        self.path = Path(path) if path is not None else base_dir / "data" / "season_state.json"
        self.phase = SeasonPhase.PRESEASON
        self.load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def load(self) -> SeasonPhase:
        """Load the season phase from disk.

        If the file does not exist or contains invalid data the phase
        defaults to ``PRESEASON`` and is saved to disk.
        """
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self.phase = SeasonPhase(data.get("phase", SeasonPhase.PRESEASON.value))
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            self.phase = SeasonPhase.PRESEASON
            self.save()
        return self.phase

    def save(self) -> None:
        """Persist the current season phase to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump({"phase": self.phase.value}, f, indent=2)

    # ------------------------------------------------------------------
    # Phase advancement
    # ------------------------------------------------------------------
    def advance_phase(self) -> SeasonPhase:
        """Advance to the next season phase and persist it."""
        self.phase = self.phase.next()
        self.save()
        return self.phase

    # ------------------------------------------------------------------
    # Phase handlers
    # ------------------------------------------------------------------
    def handle_preseason(self) -> str:
        """Handle tasks specific to the preseason phase."""
        return "Preseason: prepare teams and rosters for the year ahead."

    def handle_regular_season(self) -> str:
        """Handle tasks specific to the regular season."""
        return "Regular Season: games are underway."

    def handle_playoffs(self) -> str:
        """Handle tasks specific to the playoffs."""
        return "Playoffs: the top teams compete for the championship."

    def handle_offseason(self) -> str:
        """Handle tasks specific to the offseason."""
        return "Offseason: review performance and plan for next year."

    def handle_phase(self) -> str:
        """Dispatch to the handler for the current phase.

        Returns a descriptive note for the phase so a user interface can
        display progress information.
        """
        handlers = {
            SeasonPhase.PRESEASON: self.handle_preseason,
            SeasonPhase.REGULAR_SEASON: self.handle_regular_season,
            SeasonPhase.PLAYOFFS: self.handle_playoffs,
            SeasonPhase.OFFSEASON: self.handle_offseason,
        }
        return handlers[self.phase]()
