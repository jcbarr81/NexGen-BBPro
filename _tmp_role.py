from utils.player_loader import load_players_from_csv
from utils.pitcher_role import get_role
players = {p.player_id: p for p in load_players_from_csv('data/players.csv')}
ids = ['P3074','P4044','P9693','P2626','P7958','P5813','P1768','P7418','P8485','P3679','P4402','P2335','P7483','P4010','P5375','P7384']
for pid in ids:
    p = players[pid]
    print(pid, p.first_name, p.last_name, 'role=', get_role(p), 'is_pitcher=', getattr(p,'is_pitcher',None))
