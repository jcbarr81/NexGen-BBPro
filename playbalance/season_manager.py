from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
import shutil
from datetime import date

from utils.path_utils import get_base_dir


# Trades are prohibited after this date.
TRADE_DEADLINE = date(date.today().year, 7, 31)


class SeasonPhase(Enum):
    """Enumeration of the different phases of a season."""

    PRESEASON = "PRESEASON"
    REGULAR_SEASON = "REGULAR_SEASON"
    AMATEUR_DRAFT = "AMATEUR_DRAFT"
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
    # Pre-season utilities
    # ------------------------------------------------------------------
    def finalize_rosters(self, roster_dir: str | Path | None = None) -> None:
        """Lock roster files prior to the regular season.

        This method copies all roster CSV files into a sibling directory
        named ``rosters_locked`` and removes write permissions from the
        originals.  The copied files provide an archival snapshot while the
        permission change acts as a light-weight lock to prevent further
        modification before opening day.

        Parameters
        ----------
        roster_dir:
            Directory containing roster files.  If not provided the
            ``data/rosters`` directory relative to the project's base
            directory is used.
        """

        base_dir = get_base_dir()
        roster_path = Path(roster_dir) if roster_dir is not None else base_dir / "data" / "rosters"
        if not roster_path.is_absolute():
            roster_path = base_dir / roster_path
        if not roster_path.exists():
            return

        locked_dir = roster_path.parent / "rosters_locked"
        locked_dir.mkdir(parents=True, exist_ok=True)

        for file in roster_path.glob("*.csv"):
            shutil.copy2(file, locked_dir / file.name)
            # Do not lock pitching role files; they remain editable in-season.
            if file.name.endswith("_pitching.csv"):
                try:
                    # Ensure writable in case a previous version locked it
                    file.chmod(0o644)
                except OSError:
                    pass
                continue
            try:
                file.chmod(0o444)  # make read-only
            except OSError:
                # Permission changes may fail on some systems; ignore
                pass

    # ------------------------------------------------------------------
    # Phase handlers
    # ------------------------------------------------------------------
    def handle_preseason(self) -> str:
        """Handle tasks specific to the preseason phase."""
        return "Preseason: prepare teams and rosters for the year ahead."

    def handle_regular_season(self) -> str:
        """Handle tasks specific to the regular season."""
        return "Regular Season: games are underway."

    def handle_amateur_draft(self) -> str:
        """Handle tasks specific to the amateur draft phase."""
        return "Amateur Draft: manage draft pool, order, and selections."

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
            SeasonPhase.AMATEUR_DRAFT: self.handle_amateur_draft,
            SeasonPhase.PLAYOFFS: self.handle_playoffs,
            SeasonPhase.OFFSEASON: self.handle_offseason,
        }
        return handlers[self.phase]()
