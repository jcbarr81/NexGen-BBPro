from dataclasses import dataclass, field
from typing import List

@dataclass
class Roster:
    team_id: str
    act: List[str] = field(default_factory=list)
    aaa: List[str] = field(default_factory=list)
    low: List[str] = field(default_factory=list)
    dl: List[str] = field(default_factory=list)
    ir: List[str] = field(default_factory=list)

    def move_player(self, player_id: str, from_level: str, to_level: str):
        getattr(self, from_level).remove(player_id)
        getattr(self, to_level).append(player_id)

    def promote_replacements(self, target_size: int = 25) -> None:
        """Promote players from the minors to fill active roster vacancies.

        Parameters
        ----------
        target_size:
            Desired size of the active roster. Players are promoted from
            ``aaa`` first and then ``low`` until this size is met or no more
            players are available.
        """

        while len(self.act) < target_size and (self.aaa or self.low):
            if self.aaa:
                self.act.append(self.aaa.pop(0))
            else:
                self.act.append(self.low.pop(0))
