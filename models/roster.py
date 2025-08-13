from dataclasses import dataclass, field
from typing import List

@dataclass
class Roster:
    team_id: str
    act: List[str] = field(default_factory=list)
    aaa: List[str] = field(default_factory=list)
    low: List[str] = field(default_factory=list)

    def move_player(self, player_id: str, from_level: str, to_level: str):
        getattr(self, from_level).remove(player_id)
        getattr(self, to_level).append(player_id)
