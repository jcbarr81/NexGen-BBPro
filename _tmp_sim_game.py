from playbalance.game_runner import run_single_game
home_state, away_state, box, html, meta = run_single_game('WAS','ATL', seed=0)
print('WAS lineup size:', len(home_state.lineup))
print('WAS batters in game:', len(home_state.lineup_stats))
print('WAS hitters who batted:', [ (bs.player.player_id, bs.ab, bs.pa) for bs in home_state.lineup_stats.values()])
print('WAS bench size:', len(home_state.bench))
print('ATL hitters who batted:', len(away_state.lineup_stats))
print('Team R:', home_state.runs, 'Opp R:', away_state.runs)
