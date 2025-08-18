from logic.fielding_ai import FieldingAI
from logic.playbalance_config import PlayBalanceConfig


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
    assert not ai.should_relay_throw(fielder_time=10, runner_time=30)

    cfg = PlayBalanceConfig()
    cfg.relaySlop = -10
    ai = FieldingAI(cfg)
    assert ai.should_relay_throw(fielder_time=10, runner_time=30)


def test_tag_slop_affects_choice():
    cfg = PlayBalanceConfig()
    ai = FieldingAI(cfg)
    assert not ai.should_tag_runner(fielder_time=10, runner_time=20)

    cfg = PlayBalanceConfig()
    cfg.tagTimeSlop = -10
    ai = FieldingAI(cfg)
    assert ai.should_tag_runner(fielder_time=10, runner_time=20)


def test_run_to_bag_slop_affects_choice():
    cfg = PlayBalanceConfig()
    ai = FieldingAI(cfg)
    assert ai.should_run_to_bag(fielder_time=10, runner_time=20)

    cfg = PlayBalanceConfig()
    cfg.stepOnBagSlop = 15
    ai = FieldingAI(cfg)
    assert not ai.should_run_to_bag(fielder_time=10, runner_time=20)
