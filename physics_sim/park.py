from __future__ import annotations

from dataclasses import dataclass

from playbalance.field_geometry import Stadium
from utils.park_utils import (
    park_altitude_for_name,
    park_factor_for_name,
    park_foul_territory_for_name,
    stadium_from_name,
)


@dataclass
class Park:
    name: str
    stadium: Stadium
    park_factor: float = 1.0
    foul_territory_scale: float = 1.0
    altitude_ft: float = 0.0


def load_park(name: str | None = None) -> Park:
    """Load park geometry and factors by name, with a neutral fallback."""

    stadium = stadium_from_name(name or "") if name else None
    if stadium is None:
        stadium = Stadium()
    park_name = name or "Generic Park"
    factor = park_factor_for_name(park_name)
    foul_scale = park_foul_territory_for_name(park_name)
    altitude = park_altitude_for_name(park_name)
    return Park(
        name=park_name,
        stadium=stadium,
        park_factor=factor,
        foul_territory_scale=foul_scale,
        altitude_ft=altitude,
    )
