from dataclasses import dataclass, field
from typing import List, Optional

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

    injured: bool = False
    injury_description: Optional[str] = None
    return_date: Optional[str] = None
