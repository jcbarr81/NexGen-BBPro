import random
import pytest

from playbalance.batter_ai import BatterAI
from playbalance.state import PitcherState
from tests.test_simulation import make_player, make_pitcher
from tests.util.pbini_factory import make_cfg


def test_league_wide_swing_percentage():
    cfg = make_cfg(idRatingBase=50)
    cfg.values["swingProbScale"] = 0.76
    ai = BatterAI(cfg)
    batter = make_player("B", ch=50)
    pitcher = make_pitcher("P", movement=50)
    ps = PitcherState()
    ps.player = pitcher
    rng = random.Random(42)
    pitches = 10000
    for _ in range(pitches):
        balls = rng.randint(0, 3)
        strikes = rng.randint(0, 2)
        in_zone = rng.random() < 0.65
        if in_zone:
            dist = 0
            dx = 0.0
            dy = 0.0
        else:
            dist = 5
            dx = 5.0
            dy = 0.0
        swing, _ = ai.decide_swing(
            batter,
            pitcher,
            pitch_type="fb",
            balls=balls,
            strikes=strikes,
            dist=dist,
            dx=dx,
            dy=dy,
            random_value=rng.random(),
            check_random=rng.random(),
        )
        ps.pitches_thrown += 1
        ps.record_pitch(in_zone=in_zone, swung=swing, contact=ai.last_contact)
    swing_pct = (ps.zone_swings + ps.o_zone_swings) / ps.pitches_thrown
    assert swing_pct == pytest.approx(0.46, abs=0.03)
