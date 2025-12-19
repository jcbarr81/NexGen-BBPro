"""
Physics-based baseball simulation engine (work in progress).

This package is intentionally isolated from the legacy PB.INI-driven engine.
It consumes player ratings/park data and produces pitch-by-pitch outcomes
via physics-inspired models plus configurable tuning knobs.
"""

from .engine import simulate_game  # noqa: F401
from .config import load_tuning, TuningConfig  # noqa: F401
from .data_loader import load_players  # noqa: F401
