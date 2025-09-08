from playbalance.substitutions import (
    Team,
    pinch_hit,
    pinch_run,
    warm_reliever,
    replace_pitcher,
)
from playbalance.state import PlayerState


def make_player(name: str, fatigue: float = 0.0, **ratings: float) -> PlayerState:
    return PlayerState(name=name, ratings=ratings, fatigue=fatigue)


def test_pinch_hit_selects_best_bench_hitter():
    starter = make_player("starter", contact=40, power=40)
    bench1 = make_player("bench1", contact=50, power=50)
    bench2 = make_player("bench2", contact=80, power=80)
    team = Team(lineup=[starter], bench=[bench1, bench2])
    chosen = pinch_hit(team, 0)
    assert chosen is bench2
    assert team.lineup[0] is bench2
    assert starter in team.bench


def test_pinch_run_prefers_fast_runner():
    slow = make_player("slow", speed=40)
    fast = make_player("fast", speed=80)
    team = Team(lineup=[], bench=[fast])
    chosen = pinch_run(team, slow)
    assert chosen is fast
    assert slow in team.bench


def test_pitcher_warmup_and_replacement_with_toast():
    current = make_player("sp", fatigue=80)
    rp1 = make_player("rp1")
    rp2 = make_player("rp2")
    team = Team(lineup=[], bullpen=[rp1, rp2], current_pitcher=current)
    # Warm first reliever but switch before usage, toasting the first
    assert warm_reliever(team, 0, warmup_pitch_count=1)  # rp1 warmed
    assert not team.toasted
    assert warm_reliever(team, 1, warmup_pitch_count=1)  # rp1 toasted
    assert rp1 in team.toasted
    # Warm rp2 sufficiently and replace tired starter
    assert replace_pitcher(team, fatigue_thresh=50, warmup_pitch_count=1)
    assert team.current_pitcher is rp2
