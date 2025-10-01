from __future__ import annotations

from models.team import Team
from playbalance.playoffs import PlayoffTeam, SeriesConfig, Matchup, simulate_series


def make_team(team_id: str, league: str, seed: int) -> PlayoffTeam:
    return PlayoffTeam(team_id=team_id, seed=seed, league=league, wins=95, run_diff=100)


def always_home_wins(home: str, away: str, **kwargs):
    # Deterministic: home team wins 3-1; provide minimal html/meta
    return (3, 1, "<html>box</html>", {"extra_innings": False})


def test_simulate_series_best_of_five_pattern_and_winner():
    high = make_team("A1", "AL", 1)
    low = make_team("A4", "AL", 4)
    cfg = SeriesConfig(length=5, pattern=[2, 2, 1])
    m = Matchup(high=high, low=low, config=cfg)

    m = simulate_series(m, year=2025, round_name="AL DS", series_index=0, simulate_game=always_home_wins)
    # With home wins and 2-2-1 pattern, higher seed wins G1,G2,G5 -> 3 wins
    assert m.winner == "A1"
    # Games appended and results recorded
    assert len(m.games) >= 3
    assert all(g.result for g in m.games)

