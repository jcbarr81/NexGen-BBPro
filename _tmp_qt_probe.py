import sys
from PyQt6.QtWidgets import QApplication
from utils.team_loader import load_teams
from utils.player_loader import load_players_from_csv
from utils.roster_loader import load_roster
from ui.team_stats_window import TeamStatsWindow

app = QApplication(sys.argv)
teams = load_teams()
team = next(t for t in teams if t.team_id == 'WAS')
players = {p.player_id: p for p in load_players_from_csv('data/players.csv')}
roster = load_roster('WAS')
w = TeamStatsWindow(team, players, roster)
# Access the first tab's table widget
batting_tab = w.tabs.widget(0)
from PyQt6.QtWidgets import QTableWidget
# Find the table in the tab by type
widgets = batting_tab.findChildren(QTableWidget)
assert widgets
table = widgets[-1]
# find Jefferson row
rows = table.rowCount()
cols = table.columnCount()
print('rows, cols:', rows, cols)
# Dump first 3 rows texts for AVG/OBP/SLG columns
header_map = {table.horizontalHeaderItem(c).text(): c for c in range(cols)}
for colname in ('AVG','OBP','SLG'):
    print(colname, header_map.get(colname))
for r in range(min(3, rows)):
    name = table.item(r,0).text() if table.item(r,0) else ''
    avg = table.item(r, header_map['AVG']).text() if table.item(r, header_map['AVG']) else ''
    obp = table.item(r, header_map['OBP']).text() if table.item(r, header_map['OBP']) else ''
    slg = table.item(r, header_map['SLG']).text() if table.item(r, header_map['SLG']) else ''
    print(r, name, avg, obp, slg)
