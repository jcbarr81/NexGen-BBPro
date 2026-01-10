from __future__ import annotations

from playbalance.playoffs import (
    PlayoffTeam,
    PlayoffBracket,
    Round,
    Matchup,
    SeriesConfig,
    simulate_next_game,
)


def home_wins(home: str, away: str, **kwargs):
    return (1, 0, "<html>box</html>", {})


def test_simulate_next_game_advances_one_game_and_sets_champion():
    high = PlayoffTeam(team_id="H1", seed=1, league="LEAGUE", wins=90, run_diff=50)
    low = PlayoffTeam(team_id="L4", seed=4, league="LEAGUE", wins=80, run_diff=10)
    matchup = Matchup(
        high=high,
        low=low,
        config=SeriesConfig(length=3, pattern=[2, 1]),
    )
    bracket = PlayoffBracket(
        year=2025,
        rounds=[Round(name="Final", matchups=[matchup])],
    )

    simulate_next_game(bracket, simulate_game=home_wins, persist_cb=lambda b: None)
    assert len(matchup.games) == 1
    assert matchup.winner is None
    assert bracket.champion is None

    simulate_next_game(bracket, simulate_game=home_wins, persist_cb=lambda b: None)
    assert matchup.winner == high.team_id
    assert bracket.champion == high.team_id
    assert bracket.runner_up == low.team_id
