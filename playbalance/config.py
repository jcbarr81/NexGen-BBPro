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
from typing import Any, Dict, Iterator, Mapping
import json

from logic.pbini_loader import load_pbini


@dataclass
class SectionView(Mapping[str, Any]):
    """Expose section values with both mapping and attribute access."""

    values: Dict[str, Any]

    def __getitem__(self, key: str) -> Any:  # Mapping requirement
        return self.values[key]

    def __iter__(self) -> Iterator[str]:  # Mapping requirement
        return iter(self.values)

    def __len__(self) -> int:  # Mapping requirement
        return len(self.values)

    def get(self, key: str, default: Any | None = None) -> Any:
        return self.values.get(key, default)

    def __getattr__(self, name: str) -> Any:
        try:
            return self.values[name]
        except KeyError as exc:  # pragma: no cover - attribute error path
            raise AttributeError(name) from exc


@dataclass
class PlayBalanceConfig(Mapping[str, SectionView]):
    """Container for configuration values loaded from ``PBINI.txt``.

    The configuration may contain many sections. Each section is accessible as a
    mapping or via attribute access::

        cfg.PlayBalance.speedBase

    JSON overrides can modify or extend values without editing the original
    ``PBINI.txt``.
    """

    sections: Dict[str, SectionView]

    # ``Mapping`` protocol methods
    def __getitem__(self, section: str) -> SectionView:
        return self.sections[section]

    def __iter__(self) -> Iterator[str]:
        return iter(self.sections)

    def __len__(self) -> int:
        return len(self.sections)

    def get(self, section: str, key: str, default: Any | None = None) -> Any:
        return self.sections.get(section, SectionView({})).get(key, default)

    def __getattr__(self, name: str) -> SectionView:
        try:
            return self.sections[name]
        except KeyError as exc:  # pragma: no cover - attribute error path
            raise AttributeError(name) from exc


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
    raw_sections = load_pbini(pbini_path)

    overrides_path = Path(overrides_path)
    if overrides_path.exists():
        with overrides_path.open() as fh:
            overrides = json.load(fh)
        for key, value in overrides.items():
            if isinstance(value, dict):
                section_dict = raw_sections.setdefault(key, {})
                section_dict.update(value)
            else:
                # Allow flat key/value overrides without specifying a section.
                section_dict = raw_sections.setdefault("", {})
                section_dict[key] = value

    sections: Dict[str, SectionView] = {
        name: SectionView(values) for name, values in raw_sections.items()
    }
    return PlayBalanceConfig(sections)


__all__ = ["SectionView", "PlayBalanceConfig", "load_config"]
