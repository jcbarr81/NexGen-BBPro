from __future__ import annotations

from dataclasses import dataclass

from playbalance.field_geometry import Stadium
from utils.park_utils import stadium_from_name, park_factor_for_name


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
    factor = park_factor_for_name(name or "")
    return Park(name=name or "Generic Park", stadium=stadium, park_factor=factor)
