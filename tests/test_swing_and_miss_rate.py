import random
import pytest

from playbalance.state import PitcherState
from playbalance.stats import compute_pitching_rates
from playbalance.batter_ai import BatterAI
from tests.test_simulation import make_player, make_pitcher
from tests.util.pbini_factory import make_cfg


class DummyPitcher:
    pass


def test_swing_and_miss_rate():
    ps = PitcherState()
    ps.player = DummyPitcher()
    ps.pitches_thrown = 100
    ps.zone_swings = 25
    ps.zone_contacts = 18
    ps.o_zone_swings = 15
    ps.o_zone_contacts = 11
    rates = compute_pitching_rates(ps)
    assert rates["swstr_pct"] == pytest.approx(0.11, abs=0.01)


def test_swstr_and_bip_rates():
    cfg = make_cfg(idRatingBase=50)
    ai = BatterAI(cfg)
    batter = make_player("B", ch=50)
    pitcher = make_pitcher("P", movement=50)
    ps = PitcherState()
    ps.player = pitcher
    rng = random.Random(0)
    pitches = 10000
    contacts = 0
    for _ in range(pitches):
        swing, _ = ai.decide_swing(
            batter,
            pitcher,
            pitch_type="fb",
            balls=0,
            strikes=0,
            dist=0,
            random_value=rng.random(),
            check_random=rng.random(),
        )
        ps.pitches_thrown += 1
        contact = ai.last_contact
        ps.record_pitch(in_zone=True, swung=swing, contact=contact)
        if swing and contact:
            contacts += 1
    rates = compute_pitching_rates(ps)
    assert rates["swstr_pct"] == pytest.approx(0.11, abs=0.02)
    assert contacts / pitches < 0.38
