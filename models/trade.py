from dataclasses import dataclass
from typing import List

@dataclass
class Trade:
    trade_id: str
    from_team: str
    to_team: str
    give_player_ids: List[str]
    receive_player_ids: List[str]
    status: str = "pending"  # pending, accepted, rejected
