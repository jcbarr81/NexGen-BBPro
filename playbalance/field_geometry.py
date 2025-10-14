from __future__ import annotations

import math
from dataclasses import dataclass
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


@dataclass
class Stadium:
    """Basic outfield dimensions for a ballpark.

    Distances are measured from home plate to the wall down the left field
    line, straightaway centre field and down the right field line.  ``double``
    and ``triple`` represent the fraction of the wall distance required for a
    ball to be ruled a double or triple when it remains in the park.
    """

    left: float = 330.0
    center: float = 400.0
    right: float = 330.0
    double: float = 0.62
    triple: float = 0.92

    def wall_distance(self, angle: float) -> float:
        """Return the distance to the wall at ``angle`` in radians.

        Angle ``0`` corresponds to the right field line (positive *x*) and
        ``π/2`` to the left field line (positive *y*).  Values in between are
        linearly interpolated between the provided corner distances.
        """

        half = math.pi / 4
        if angle <= half:
            return self.right + (self.center - self.right) * angle / half
        return self.center + (self.left - self.center) * (angle - half) / half

    def double_distance(self, angle: float) -> float:
        """Threshold distance for a double at ``angle``."""

        return self.wall_distance(angle) * self.double

    def triple_distance(self, angle: float) -> float:
        """Threshold distance for a triple at ``angle``."""

        return self.wall_distance(angle) * self.triple

__all__ = [
    "HOME",
    "FIRST_BASE",
    "SECOND_BASE",
    "THIRD_BASE",
    "PITCHER",
    "DEFAULT_POSITIONS",
    "Stadium",
]
