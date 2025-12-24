from dataclasses import dataclass, field
from typing import ClassVar

from models.base_player import BasePlayer


@dataclass
class Pitcher(BasePlayer):
    _rating_fields: ClassVar[set[str]] = BasePlayer._rating_fields | {
        "endurance",
        "control",
        "movement",
        "hold_runner",
        "fb",
        "cu",
        "cb",
        "sl",
        "si",
        "scb",
        "kn",
        "arm",
        "fa",
    }

    ethnicity: str = ""
    skin_tone: str = ""
    hair_color: str = ""
    facial_hair: str = ""
    pitcher_archetype: str = ""

    endurance: int = 0
    control: int = 0
    movement: int = 0
    hold_runner: int = 0
    role: str = ""
    preferred_pitching_role: str = ""
    is_pitcher: bool = True
    fatigue: str = "fresh"

    fb: int = 0
    cu: int = 0
    cb: int = 0
    sl: int = 0
    si: int = 0
    scb: int = 0
    kn: int = 0

    # Core physical/fielding ratings
    arm: int = 0
    fa: int = 0

    # Stores potential ratings keyed by rating name
    potential: dict = field(default_factory=dict)
