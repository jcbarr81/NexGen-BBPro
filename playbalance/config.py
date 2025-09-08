"""Configuration loader for the play-balance engine.

This module reads tuning values from the project's ``PBINI.txt`` file.  The
file follows a simple INI-style structure and all entries are exposed through
the :class:`PlayBalanceConfig` dataclass.  An optional JSON file may supply
override values without touching the original configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import json

from logic.pbini_loader import load_pbini


@dataclass
class PlayBalanceConfig:
    """Container for configuration sections loaded from ``PBINI.txt``.

    The underlying data structure mirrors the INI format: a mapping of section
    names to dictionaries of key/value pairs.  Convenience attribute access is
    provided for the ``PlayBalance`` section which contains the majority of
    simulation tuning values.
    """

    sections: Dict[str, Dict[str, Any]]

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------
    def get(self, section: str, key: str, default: Any | None = None) -> Any:
        """Return a configuration value from ``section`` or ``default``."""

        return self.sections.get(section, {}).get(key, default)

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - delegation
        """Expose ``PlayBalance`` entries as attributes returning ``0`` when
        missing.
        """

        return self.get("PlayBalance", item, 0)


def load_config(
    pbini_path: str | Path = Path("logic/PBINI.txt"),
    overrides_path: str | Path = Path("data/playbalance_overrides.json"),
) -> PlayBalanceConfig:
    """Load configuration from ``pbini_path`` and optional JSON overrides."""

    sections = load_pbini(pbini_path)

    overrides_path = Path(overrides_path)
    if overrides_path.exists():
        try:
            with overrides_path.open("r", encoding="utf-8") as fh:
                overrides = json.load(fh)
        except json.JSONDecodeError:
            overrides = {}

        if isinstance(overrides, dict):
            for sect, values in overrides.items():
                if isinstance(values, dict):
                    section_dict = sections.setdefault(sect, {})
                    section_dict.update(values)
                else:
                    # Allow flat overrides applied to a default section.
                    section_dict = sections.setdefault("", {})
                    section_dict[sect] = values

    return PlayBalanceConfig(sections)


__all__ = ["PlayBalanceConfig", "load_config"]

