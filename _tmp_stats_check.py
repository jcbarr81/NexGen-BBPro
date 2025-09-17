import json
from pathlib import Path
stats = json.load(Path('data/season_stats.json').open())
for pid, data in stats.get('players', {}).items():
    if 'era' in data or 'ip' in data:
        print(pid, data.get('era'), data.get('ip'))
        break
