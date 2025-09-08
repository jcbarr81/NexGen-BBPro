"""Configuration loader for the play-balance engine.

This module reads tuning values from the project's ``PBINI.txt`` file.  The
file follows a simple INI-style structure and all entries are exposed through
the :class:`PlayBalanceConfig` dataclass.  An optional JSON file may supply
override values without touching the original configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, make_dataclass
from pathlib import Path
from typing import Any, Dict
import json

from logic.pbini_loader import load_pbini


@dataclass
class PlayBalanceConfig:
    """Container for configuration sections loaded from ``PBINI.txt``.

    Each section from the INI file is converted into its own dataclass where
    every key becomes a typed attribute.  This provides attribute completion
    while still allowing dynamic loading of the configuration file.  The raw
    sections are preserved in :attr:`sections` for introspection.
    """

    sections: Dict[str, Any]

    def __post_init__(self) -> None:
        """Turn plain section dictionaries into dataclass instances."""

        typed_sections: Dict[str, Any] = {}
        for name, values in self.sections.items():
            fields = [(k, type(v), field(default=v)) for k, v in values.items()]
            SectionCls = make_dataclass(name, fields)
            section_obj = SectionCls(**values)
            setattr(self, name, section_obj)
            typed_sections[name] = section_obj
        self.sections = typed_sections

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------
    def get(self, section: str, key: str, default: Any | None = None) -> Any:
        """Return a configuration value from ``section`` or ``default``."""

        sect = self.sections.get(section)
        return getattr(sect, key, default) if sect else default

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - delegation
        """Expose ``PlayBalance`` entries as attributes returning ``0`` when
        missing."""

        sect = self.sections.get("PlayBalance")
        return getattr(sect, item, 0) if sect else 0


def load_config(
    pbini_path: str | Path = Path("logic/PBINI.txt"),
    overrides_path: str | Path = Path("data/playbalance_overrides.json"),
) -> PlayBalanceConfig:
    """Load configuration from ``pbini_path`` and optional JSON overrides."""

    sections = load_pbini(pbini_path)
    # Preserve the original keys to ensure coverage after overrides are merged.
    pbini_keys = {sect: set(vals.keys()) for sect, vals in sections.items()}

    overrides_path = Path(overrides_path)
    if overrides_path.exists():
        try:
            with overrides_path.open("r", encoding="utf-8") as fh:
                overrides = json.load(fh)
        except json.JSONDecodeError:
            overrides = {}

        if isinstance(overrides, dict):
            # Determine which section should receive flat overrides.  By
            # convention the PBINI file uses a single "PlayBalance" section,
            # but fall back to the first loaded section for flexibility.
            default_section = "PlayBalance"
            if default_section not in sections and sections:
                default_section = next(iter(sections))

            for sect, values in overrides.items():
                if isinstance(values, dict):
                    if sect not in sections:
                        raise KeyError(f"Unknown config section '{sect}'")
                    unknown = set(values) - pbini_keys.get(sect, set())
                    if unknown:
                        unknown_list = ", ".join(sorted(unknown))
                        raise KeyError(f"Unknown keys for section '{sect}': {unknown_list}")
                    section_dict = sections.setdefault(sect, {})
                    section_dict.update(values)
                else:
                    # Allow flat overrides applied to the default section.
                    if sect not in pbini_keys.get(default_section, set()):
                        raise KeyError(f"Unknown key '{sect}' for section '{default_section}'")
                    section_dict = sections.setdefault(default_section, {})
                    section_dict[sect] = values

    # Ensure that all PBINI keys remain represented after merging overrides.
    for sect, keys in pbini_keys.items():
        missing = keys - set(sections.get(sect, {}).keys())
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise KeyError(f"Missing keys from section '{sect}': {missing_list}")

    return PlayBalanceConfig(sections)


__all__ = ["PlayBalanceConfig", "load_config"]

