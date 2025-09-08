"""Configuration loader for the play-balance engine.

The classic project stores simulation tuning values in a ``PBINI.txt`` file
using an ``INI``-like format. This module provides a thin wrapper around the
:func:`logic.pbini_loader.load_pbini` function and exposes the data through a
simple dataclass. An optional JSON overrides file can supply adjustments
without modifying the original configuration file.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import json

from logic.pbini_loader import load_pbini


@dataclass
class PlayBalanceConfig:
    """Container for configuration values loaded from ``PBINI.txt``.

    Attributes
    ----------
    sections:
        Mapping of section names to dictionaries of key/value pairs.
    """

    sections: Dict[str, Dict[str, Any]]

    def get(self, section: str, key: str, default: Any | None = None) -> Any:
        """Return a configuration value.

        Parameters
        ----------
        section:
            Name of the section in the configuration file.
        key:
            The configuration key within ``section``.
        default:
            Value returned when the key is missing.
        """
        return self.sections.get(section, {}).get(key, default)


def load_config(
    pbini_path: str | Path = Path("logic/PBINI.txt"),
    overrides_path: str | Path = Path("data/playbalance_overrides.json"),
) -> PlayBalanceConfig:
    """Load configuration from ``PBINI.txt`` and optional overrides.

    Parameters
    ----------
    pbini_path:
        Location of the ``PBINI.txt`` file.
    overrides_path:
        JSON file containing ``{"Section": {"Key": value}}`` overrides.
    """
    sections = load_pbini(pbini_path)

    overrides_path = Path(overrides_path)
    if overrides_path.exists():
        with overrides_path.open() as fh:
            overrides = json.load(fh)
        for key, value in overrides.items():
            if isinstance(value, dict):
                section_dict = sections.setdefault(key, {})
                section_dict.update(value)
            else:
                # Allow flat key/value overrides without specifying a section.
                section_dict = sections.setdefault("", {})
                section_dict[key] = value

    return PlayBalanceConfig(sections)


__all__ = ["PlayBalanceConfig", "load_config"]
