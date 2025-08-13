from dataclasses import dataclass, field
from typing import List
import re

@dataclass
class Team:
    """Represents a team in the league.

    Attributes:
        primary_color: Hex color string (e.g. "#RRGGBB").
        secondary_color: Hex color string (e.g. "#RRGGBB").
    """

    team_id: str
    name: str
    city: str
    abbreviation: str
    division: str
    stadium: str
    primary_color: str  # Hex color string
    secondary_color: str  # Hex color string
    owner_id: str

    act_roster: List[str] = field(default_factory=list)
    aaa_roster: List[str] = field(default_factory=list)
    low_roster: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate color fields after initialization."""
        for attr in ("primary_color", "secondary_color"):
            value = getattr(self, attr)
            if not self._is_hex_color(value):
                raise ValueError(
                    f"{attr} must be a hex color string like '#RRGGBB'"
                )

    @staticmethod
    def _is_hex_color(value: str) -> bool:
        """Return True if *value* is a valid hex color string."""
        return bool(re.fullmatch(r"#(?:[0-9a-fA-F]{3}){1,2}$", value))
