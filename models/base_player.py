from dataclasses import dataclass
from typing import ClassVar, List, Optional

@dataclass
class BasePlayer:
    player_id: str
    first_name: str
    last_name: str
    birthdate: str
    height: int
    weight: int
    bats: str
    primary_position: str
    other_positions: List[str]
    gf: int  # Groundball-Flyball ratio

    # Appearance attributes
    ethnicity: str = ""
    skin_tone: str = ""
    hair_color: str = ""
    facial_hair: str = ""

    injured: bool = False
    injury_description: Optional[str] = None
    return_date: Optional[str] = None
    is_pitcher: bool = False
    # Flag indicating if the player is ready after training camp
    ready: bool = False

    _rating_fields: ClassVar[set[str]] = {"gf"}

    def __setattr__(self, name: str, value) -> None:
        rating_fields = getattr(type(self), "_rating_fields", set())
        if name in rating_fields and isinstance(value, (int, float)):
            value = 99 if value > 99 else int(value)
        super().__setattr__(name, value)
