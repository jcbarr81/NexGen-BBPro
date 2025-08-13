from __future__ import annotations

from pathlib import Path

from logic.playbalance_config import PlayBalanceConfig
from logic.pbini_loader import load_pbini


def make_cfg(**entries: int) -> PlayBalanceConfig:
    """Return a :class:`PlayBalanceConfig` with ``entries`` overridden.

    Only the provided entries are included; unspecified keys fall back to the
    defaults provided by :class:`PlayBalanceConfig` when accessed.
    """

    return PlayBalanceConfig.from_dict({"PlayBalance": entries})


def load_config() -> PlayBalanceConfig:
    """Load the full test configuration from ``logic/PBINI.txt``."""

    pbini = load_pbini(Path("logic/PBINI.txt"))
    return PlayBalanceConfig.from_dict(pbini)
