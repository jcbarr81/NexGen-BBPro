import random

import pytest

from playbalance.simulation import (
    BatterState,
    GameSimulation,
    TeamState,
)
from playbalance.state import PitcherState
from tests.test_physics import make_player, make_pitcher
from tests.util.pbini_factory import make_cfg


class ZeroRandom(random.Random):
    """Deterministic random source returning 0 for all calls."""

    def random(self):  # type: ignore[override]
        return 0.0

    def randint(self, a, b):  # type: ignore[override]
        return a


@pytest.mark.parametrize(
    "rates, action, needs_throw",
    [
        (
            {
                "groundBallBaseRate": 100,
                "lineDriveBaseRate": 0,
                "flyBallBaseRate": 0,
            },
            "throw",
            True,
        ),
        (
            {
                "groundBallBaseRate": 0,
                "lineDriveBaseRate": 100,
                "flyBallBaseRate": 0,
            },
            "catch",
            False,
        ),
        (
            {
                "groundBallBaseRate": 0,
                "lineDriveBaseRate": 0,
                "flyBallBaseRate": 100,
            },
            "catch",
            False,
        ),
    ],
)
def test_ball_in_play_outs(monkeypatch, rates, action, needs_throw):
    cfg = make_cfg(hitProbCap=1.0, **rates)
    home = TeamState(
        lineup=[make_player("h1")],
        bench=[],
        pitchers=[make_pitcher("hp")],
    )
    away = TeamState(
        lineup=[make_player("a1")],
        bench=[],
        pitchers=[make_pitcher("ap")],
    )
    rng = ZeroRandom()
    sim = GameSimulation(home, away, cfg, rng)

    from playbalance.field_geometry import DEFAULT_POSITIONS

    px, py = DEFAULT_POSITIONS["P"]
    monkeypatch.setattr(
        sim.physics, "landing_point", lambda vx, vy, vz: (px, py, 1.0)
    )
    monkeypatch.setattr(
        sim.physics, "ball_roll_distance", lambda *args, **kwargs: 0.0
    )
    monkeypatch.setattr(sim.physics, "ball_bounce", lambda *args, **kwargs: (0.0, 0.0))
    monkeypatch.setattr(sim.fielding_ai, "catch_action", lambda *a, **k: action)

    catch_calls: list[bool] = []

    def fake_catch_probability(*args, **kwargs):
        catch_calls.append(True)
        return 1.0

    monkeypatch.setattr(sim.fielding_ai, "catch_probability", fake_catch_probability)

    throw_calls: list[bool] = []

    def fake_resolve_throw(*args, **kwargs):
        throw_calls.append(True)
        return True, False

    monkeypatch.setattr(sim.fielding_ai, "resolve_throw", fake_resolve_throw)

    batter = away.lineup[0]
    pitcher = home.pitchers[0]
    batter_state = BatterState(batter)
    pitcher_state = PitcherState()
    pitcher_state.player = pitcher
    bases, error = sim._swing_result(
        batter,
        pitcher,
        home,
        batter_state,
        pitcher_state,
        pitch_speed=50,
    )
    assert bases == 0 and not error
    assert all(base is None for base in away.bases)
    assert catch_calls  # fielding resolved the play
    if needs_throw:
        assert throw_calls

