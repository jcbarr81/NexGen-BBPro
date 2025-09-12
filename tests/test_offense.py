from playbalance import (
    load_config,
    steal_chance,
    maybe_attempt_steal,
    hit_and_run_chance,
    maybe_hit_and_run,
    sacrifice_bunt_chance,
    maybe_sacrifice_bunt,
    squeeze_chance,
    maybe_squeeze,
)


cfg = load_config()


def test_steal_chance_increases_with_speed():
    slow = steal_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=30,
        pitcher_hold=50,
        pitcher_is_left=True,
    )
    fast = steal_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        pitcher_hold=50,
        pitcher_is_left=True,
    )
    assert 0.0 <= slow <= fast <= 1.0


def test_steal_chance_pitcher_hold_thresholds():
    """Pitcher hold ability heavily influences steal attempts."""

    weak_hold = steal_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        pitcher_hold=10,
        pitcher_is_left=False,
    )
    strong_hold = steal_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        pitcher_hold=80,
        pitcher_is_left=False,
    )
    assert weak_hold > strong_hold


def test_steal_chance_on_second_and_outs():
    """Second base steal chance depends on outs and contact."""

    one_out = steal_chance(
        cfg,
        balls=1,
        strikes=0,
        runner_sp=80,
        pitcher_hold=20,
        pitcher_is_left=False,
        outs=1,
        runner_on=2,
        batter_ch=80,
    )
    zero_outs = steal_chance(
        cfg,
        balls=1,
        strikes=0,
        runner_sp=80,
        pitcher_hold=20,
        pitcher_is_left=False,
        outs=0,
        runner_on=2,
        batter_ch=80,
    )
    two_outs = steal_chance(
        cfg,
        balls=1,
        strikes=0,
        runner_sp=80,
        pitcher_hold=20,
        pitcher_is_left=False,
        outs=2,
        runner_on=2,
        batter_ch=50,
    )
    assert one_out > zero_outs > two_outs


def test_hit_and_run_requires_runner_on_first():
    chance = hit_and_run_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
        runner_on_first=False,
    )
    assert chance == 0.0


class DummyRoll:
    def __init__(self, result: bool):
        self.result = result

    def __call__(self, chance: float) -> bool:  # pragma: no cover - simple stub
        return self.result


def test_decision_helpers(monkeypatch):
    # Force a successful roll
    monkeypatch.setattr("playbalance.offense.roll", DummyRoll(True))
    assert maybe_attempt_steal(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        pitcher_hold=40,
        pitcher_is_left=False,
    )
    assert maybe_hit_and_run(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        batter_ch=80,
        batter_ph=20,
    )
    assert maybe_sacrifice_bunt(
        cfg,
        batter_ch=50,
        on_deck_ch=60,
        on_deck_ph=60,
        outs=1,
        inning=7,
        run_diff=0,
        runner_on_first=True,
    )
    assert maybe_squeeze(
        cfg,
        kind="suicide",
        balls=0,
        strikes=0,
        batter_ch=50,
        batter_ph=50,
        runner_on_third_sp=60,
    )
    # Force a failed roll
    monkeypatch.setattr("playbalance.offense.roll", DummyRoll(False))
    assert not maybe_attempt_steal(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        pitcher_hold=40,
        pitcher_is_left=False,
    )
    assert not maybe_hit_and_run(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        batter_ch=80,
        batter_ph=20,
    )
    assert not maybe_sacrifice_bunt(
        cfg,
        batter_ch=50,
        on_deck_ch=60,
        on_deck_ph=60,
        outs=1,
        inning=7,
        run_diff=0,
        runner_on_first=True,
    )
    assert not maybe_squeeze(
        cfg,
        kind="suicide",
        balls=0,
        strikes=0,
        batter_ch=50,
        batter_ph=50,
        runner_on_third_sp=60,
    )


def test_squeeze_safety_lower_than_suicide():
    suicide = squeeze_chance(
        cfg,
        kind="suicide",
        balls=0,
        strikes=0,
        batter_ch=60,
        batter_ph=60,
        runner_on_third_sp=60,
    )
    safety = squeeze_chance(
        cfg,
        kind="safety",
        balls=0,
        strikes=0,
        batter_ch=60,
        batter_ph=60,
        runner_on_third_sp=60,
    )
    assert 0.0 <= safety <= suicide <= 1.0


def test_hit_and_run_chance_increases_with_modifiers():
    """Fast runners and high-contact hitters raise H&R probability."""

    low = hit_and_run_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=30,
        batter_ch=50,
        batter_ph=50,
    )
    high = hit_and_run_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=80,
        batter_ch=80,
        batter_ph=20,
    )
    assert 0.0 <= low <= high <= 1.0


def test_hit_and_run_chance_game_situations():
    """Run deficit and base state alter H&R probability."""

    base = hit_and_run_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
    )
    behind = hit_and_run_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
        run_diff=-3,
    )
    on_first_second = hit_and_run_chance(
        cfg,
        balls=0,
        strikes=0,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
        runner_on_second=True,
    )

    assert behind < base
    assert on_first_second < base


def test_hit_and_run_chance_count_modifiers():
    """Three balls raise and two strikes lower the chance."""

    two_ball = hit_and_run_chance(
        cfg,
        balls=2,
        strikes=0,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
    )
    three_ball = hit_and_run_chance(
        cfg,
        balls=3,
        strikes=0,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
    )
    even_count = hit_and_run_chance(
        cfg,
        balls=1,
        strikes=1,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
    )
    two_strike = hit_and_run_chance(
        cfg,
        balls=0,
        strikes=2,
        runner_sp=60,
        batter_ch=60,
        batter_ph=40,
    )

    assert two_ball < three_ball
    assert two_strike < even_count


def test_sacrifice_bunt_situational_modifiers():
    """Sacrifice chance depends on base state and game context."""

    none = sacrifice_bunt_chance(
        cfg,
        batter_ch=50,
        on_deck_ch=50,
        on_deck_ph=50,
        outs=0,
        inning=1,
        run_diff=0,
        runner_on_first=False,
    )
    early = sacrifice_bunt_chance(
        cfg,
        batter_ch=50,
        on_deck_ch=50,
        on_deck_ph=50,
        outs=0,
        inning=1,
        run_diff=2,
        runner_on_first=True,
    )
    late = sacrifice_bunt_chance(
        cfg,
        batter_ch=50,
        on_deck_ch=50,
        on_deck_ph=50,
        outs=0,
        inning=8,
        run_diff=0,
        runner_on_first=True,
    )
    assert none == 0.0
    assert 0.0 <= early <= late <= 1.0


