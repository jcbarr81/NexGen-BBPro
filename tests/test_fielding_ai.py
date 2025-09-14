from random import Random

from playbalance.fielding_ai import FieldingAI
from playbalance.playbalance_config import PlayBalanceConfig


def test_catch_slop_changes_decision():
    cfg = PlayBalanceConfig()
    ai = FieldingAI(cfg)
    # With default slop the fielder will dive for the ball
    assert ai.catch_action(hang_time=60, run_time=55) == "dive"

    # Increasing the slop pushes the decision to ignore the ball
    cfg = PlayBalanceConfig()
    cfg.couldBeCaughtSlop = 20
    ai = FieldingAI(cfg)
    assert ai.catch_action(hang_time=60, run_time=55) == "no_attempt"


def test_relay_slop_affects_choice():
    cfg = PlayBalanceConfig()
    ai = FieldingAI(cfg)
    assert not ai.should_relay_throw(fielder_time=1.0, runner_time=1.1)

    cfg = PlayBalanceConfig()
    cfg.relaySlop = -10
    ai = FieldingAI(cfg)
    assert ai.should_relay_throw(fielder_time=1.0, runner_time=1.1)


def test_tag_slop_affects_choice():
    cfg = PlayBalanceConfig()
    ai = FieldingAI(cfg)
    assert not ai.should_tag_runner(fielder_time=1.0, runner_time=1.05)

    cfg = PlayBalanceConfig()
    cfg.tagTimeSlop = -10
    ai = FieldingAI(cfg)
    assert ai.should_tag_runner(fielder_time=1.0, runner_time=1.05)


def test_run_to_bag_slop_affects_choice():
    cfg = PlayBalanceConfig()
    ai = FieldingAI(cfg)
    assert ai.should_run_to_bag(fielder_time=1.0, runner_time=1.05)

    cfg = PlayBalanceConfig()
    cfg.stepOnBagSlop = 15
    ai = FieldingAI(cfg)
    assert not ai.should_run_to_bag(fielder_time=1.0, runner_time=1.05)


def test_higher_fa_reduces_throw_errors():
    cfg = PlayBalanceConfig()
    cfg.goodThrowBase = 50
    cfg.goodThrowFAPct = 50
    ai = FieldingAI(cfg)
    low_error = 1 - ai.good_throw_probability("SS", fa=10)
    high_error = 1 - ai.good_throw_probability("SS", fa=90)
    assert high_error < low_error


def test_outfielders_have_throw_penalty():
    cfg = PlayBalanceConfig()
    cfg.goodThrowBase = 50
    cfg.goodThrowChanceLeftField = -10
    ai = FieldingAI(cfg)
    infield = ai.good_throw_probability("SS", fa=50)
    outfield = ai.good_throw_probability("LF", fa=50)
    assert outfield < infield


def test_bad_throw_sets_error_state():
    cfg = PlayBalanceConfig()
    cfg.goodThrowBase = 0
    cfg.goodThrowFAPct = 0
    ai = FieldingAI(cfg, rng=Random(0))
    caught, error = ai.resolve_throw("SS", fa=0, hang_time=1.0)
    assert error


def test_infielder_chase_limit():
    cfg = PlayBalanceConfig()
    cfg.infieldMaxChaseDist = 50
    ai = FieldingAI(cfg)
    # Distance beyond limit results in no attempt despite ample hang time
    action = ai.catch_action(
        hang_time=60,
        run_time=10,
        position="SS",
        distance=60,
    )
    assert action == "no_attempt"

    # At the limit the fielder will pursue the ball
    action = ai.catch_action(
        hang_time=60,
        run_time=10,
        position="SS",
        distance=50,
    )
    assert action == "catch"


def test_pitcher_chase_limit():
    cfg = PlayBalanceConfig()
    cfg.pitcherMaxChaseDist = 90
    ai = FieldingAI(cfg)
    action = ai.catch_action(
        hang_time=60,
        run_time=10,
        position="P",
        distance=100,
    )
    assert action == "no_attempt"

    action = ai.catch_action(
        hang_time=60,
        run_time=10,
        position="P",
        distance=90,
    )
    assert action == "catch"


def test_outfielder_chase_limit():
    cfg = PlayBalanceConfig()
    cfg.outfieldMinChaseDist = 150
    ai = FieldingAI(cfg)
    action = ai.catch_action(
        hang_time=60,
        run_time=10,
        position="CF",
        distance=10,
        dist_from_home=140,
    )
    assert action == "no_attempt"

    action = ai.catch_action(
        hang_time=60,
        run_time=10,
        position="CF",
        distance=10,
        dist_from_home=150,
    )
    assert action == "catch"
