from physics_sim.config import TuningConfig
from physics_sim.engine import _advance_prob, _steal_attempt_rate, _steal_success_prob
from physics_sim.fielding import double_play_probability, error_probability


def test_steal_attempt_rate_responds_to_speed_and_arm() -> None:
    tuning = TuningConfig()
    base_rate = 0.02

    rate_fast = _steal_attempt_rate(
        speed=80.0,
        base_rate=base_rate,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    rate_slow = _steal_attempt_rate(
        speed=40.0,
        base_rate=base_rate,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    assert rate_fast > rate_slow

    rate_strong_arm = _steal_attempt_rate(
        speed=60.0,
        base_rate=base_rate,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=80.0,
        catcher_fielding=80.0,
        tuning=tuning,
    )
    rate_weak_arm = _steal_attempt_rate(
        speed=60.0,
        base_rate=base_rate,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=20.0,
        catcher_fielding=20.0,
        tuning=tuning,
    )
    assert rate_strong_arm < rate_weak_arm

    rate_quick_arm = _steal_attempt_rate(
        speed=60.0,
        base_rate=base_rate,
        pitcher_hold=50.0,
        pitcher_arm=80.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    rate_slow_arm = _steal_attempt_rate(
        speed=60.0,
        base_rate=base_rate,
        pitcher_hold=50.0,
        pitcher_arm=20.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    assert rate_quick_arm < rate_slow_arm


def test_steal_success_prob_responds_to_speed_and_arm() -> None:
    tuning = TuningConfig()

    success_fast = _steal_success_prob(
        speed=80.0,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    success_slow = _steal_success_prob(
        speed=40.0,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    assert success_fast > success_slow

    success_strong_arm = _steal_success_prob(
        speed=60.0,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=80.0,
        catcher_fielding=80.0,
        tuning=tuning,
    )
    success_weak_arm = _steal_success_prob(
        speed=60.0,
        pitcher_hold=50.0,
        pitcher_arm=50.0,
        catcher_arm=20.0,
        catcher_fielding=20.0,
        tuning=tuning,
    )
    assert success_strong_arm < success_weak_arm

    success_quick_arm = _steal_success_prob(
        speed=60.0,
        pitcher_hold=50.0,
        pitcher_arm=80.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    success_slow_arm = _steal_success_prob(
        speed=60.0,
        pitcher_hold=50.0,
        pitcher_arm=20.0,
        catcher_arm=50.0,
        catcher_fielding=50.0,
        tuning=tuning,
    )
    assert success_quick_arm < success_slow_arm


def test_tag_up_prob_decreases_with_arm_strength() -> None:
    tuning = TuningConfig()
    prob_strong_arm = _advance_prob(speed=50.0, arm=80.0, tuning=tuning, extra=0.0)
    prob_weak_arm = _advance_prob(speed=50.0, arm=20.0, tuning=tuning, extra=0.0)
    assert prob_strong_arm < prob_weak_arm


def test_double_play_probability_tracks_infield_quality() -> None:
    tuning = TuningConfig()
    prob_good = double_play_probability(
        runner_speed=50.0,
        infield_range=70.0,
        turn_arm=70.0,
        tuning=tuning,
    )
    prob_poor = double_play_probability(
        runner_speed=50.0,
        infield_range=30.0,
        turn_arm=30.0,
        tuning=tuning,
    )
    assert prob_good > prob_poor


def test_error_probability_drops_with_fielding() -> None:
    tuning = TuningConfig()
    prob_good = error_probability(
        out_type="groundout",
        infield_play=True,
        fielding=80.0,
        arm=80.0,
        tuning=tuning,
    )
    prob_poor = error_probability(
        out_type="groundout",
        infield_play=True,
        fielding=30.0,
        arm=30.0,
        tuning=tuning,
    )
    assert prob_good < prob_poor
