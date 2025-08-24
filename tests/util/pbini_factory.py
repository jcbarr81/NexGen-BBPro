from __future__ import annotations

from pathlib import Path

from logic.playbalance_config import PlayBalanceConfig
from logic.pbini_loader import load_pbini


def make_cfg(**entries: int) -> PlayBalanceConfig:
    """Return a :class:`PlayBalanceConfig` with ``entries`` overridden.

    Tests expect deterministic at-bats, so base hit probabilities default to a
    guaranteed single unless explicitly overridden.  Remaining unspecified keys
    fall back to :class:`PlayBalanceConfig` defaults when accessed.
    """

    base_entries = {"hit1BProb": 100, "hit2BProb": 0, "hit3BProb": 0, "hitHRProb": 0}
    base_entries.update(entries)
    return PlayBalanceConfig.from_dict({"PlayBalance": base_entries})


def load_config(path: Path | None = None) -> PlayBalanceConfig:
    """Load the full test configuration from ``path``.

    If ``path`` is ``None`` the default ``logic/PBINI.txt`` is used.  This
    helper allows tests to provide their own PlayBalance files when specific
    values need to be exercised.
    """

    path = Path("logic/PBINI.txt") if path is None else Path(path)
    pbini = load_pbini(path)
    cfg = PlayBalanceConfig.from_dict(pbini)
    # Default to singles only for deterministic tests unless overridden later
    cfg.values.update({"hit1BProb": 100, "hit2BProb": 0, "hit3BProb": 0, "hitHRProb": 0})
    # The real configuration contains pitch objective weights which would
    # introduce additional randomness via :class:`PitcherAI`.  Tests expect
    # deterministic behaviour so clear all such weights.
    for balls in range(4):
        for strikes in range(3):
            prefix = f"pitchObj{balls}{strikes}Count"
            for suffix in [
                "EstablishWeight",
                "OutsideWeight",
                "BestWeight",
                "BestCenterWeight",
                "FastCenterWeight",
                "PlusWeight",
            ]:
                cfg.values[f"{prefix}{suffix}"] = 0
    return cfg
