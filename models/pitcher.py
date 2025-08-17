from dataclasses import dataclass, field
from models.base_player import BasePlayer


@dataclass
class Pitcher(BasePlayer):
    endurance: int = 0
    control: int = 0
    movement: int = 0
    hold_runner: int = 0
    role: str = ""
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
