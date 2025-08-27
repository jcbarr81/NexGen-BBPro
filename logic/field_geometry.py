from __future__ import annotations

from math import sqrt

# Coordinates are measured in feet with home plate at (0, 0).
# The x-axis extends toward first base and the y-axis toward third base.
HOME = (0.0, 0.0)
FIRST_BASE = (90.0, 0.0)
SECOND_BASE = (90.0, 90.0)
THIRD_BASE = (0.0, 90.0)
PITCHER = (60.5 / sqrt(2), 60.5 / sqrt(2))

# Approximate default defensive positions.
DEFAULT_POSITIONS = {
    "P": PITCHER,
    "C": (-5.0, 0.0),
    "1B": FIRST_BASE,
    "2B": (100.0, 40.0),
    "3B": THIRD_BASE,
    "SS": (40.0, 100.0),
    "LF": (0.0, 300.0),
    "CF": (283.0, 283.0),
    "RF": (300.0, 0.0),
}

__all__ = [
    "HOME",
    "FIRST_BASE",
    "SECOND_BASE",
    "THIRD_BASE",
    "PITCHER",
    "DEFAULT_POSITIONS",
]
