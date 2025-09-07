import random

import pytest

from logic.simulation import GameSimulation, TeamState
from tests.test_physics import make_player, make_pitcher
from tests.util.pbini_factory import make_cfg


class ZeroRandom(random.Random):
    """Deterministic random source returning 0 for all calls."""

    def random(self):  # type: ignore[override]
        return 0.0

    def randint(self, a, b):  # type: ignore[override]
        return a


@pytest.mark.parametrize(
    "out_key, rates",
    [
        (
            "groundOutProb",
            {
                "groundBallBaseRate": 100,
                "lineDriveBaseRate": 0,
                "flyBallBaseRate": 0,
            },
        ),
        (
            "lineOutProb",
            {
                "groundBallBaseRate": 0,
                "lineDriveBaseRate": 100,
                "flyBallBaseRate": 0,
            },
        ),
        (
            "flyOutProb",
            {
                "groundBallBaseRate": 0,
                "lineDriveBaseRate": 0,
                "flyBallBaseRate": 100,
            },
        ),
    ],
)
def test_ball_in_play_outs(out_key, rates):
    cfg = make_cfg(
        hitProbCap=1.0,
        groundOutProb=0.0,
        lineOutProb=0.0,
        flyOutProb=0.0,
        **rates,
    )
    setattr(cfg, out_key, 1.0)
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
    outs = sim.play_at_bat(away, home)
    assert outs == 1
    assert all(base is None for base in away.bases)

