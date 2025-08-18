from logic.batter_ai import BatterAI
from tests.util.pbini_factory import load_config
from tests.test_simulation import make_player, make_pitcher


def test_swing_decision_respects_idrating():
    cfg = load_config()
    cfg.values.update({"idRatingBase": 100})
    ai = BatterAI(cfg)
    batter = make_player("b1")
    pitcher = make_pitcher("p1")
    swing, contact = ai.decide_swing(
        batter,
        pitcher,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.0,
    )
    assert swing is True
    assert contact == 1.0


def test_misidentification_reduces_contact():
    cfg = load_config()
    cfg.values.update({"idRatingBase": 0})
    ai = BatterAI(cfg)
    batter = make_player("b1")
    pitcher = make_pitcher("p1")
    swing, contact = ai.decide_swing(
        batter,
        pitcher,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.4,
    )
    assert swing is True
    assert contact == 0.5


def test_primary_look_adjust_increases_swings():
    cfg = load_config()
    cfg.values.update({"idRatingBase": 0, "lookPrimaryType00CountAdjust": 50})
    ai = BatterAI(cfg)
    batter = make_player("b1")
    pitcher = make_pitcher("p1")
    swing, contact = ai.decide_swing(
        batter,
        pitcher,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.4,
    )
    assert swing is True
    assert contact == 1.0


def test_best_look_adjust_increases_swings():
    cfg = load_config()
    cfg.values.update({"idRatingBase": 0, "lookBestType00CountAdjust": 50})
    ai = BatterAI(cfg)
    batter = make_player("b1")
    pitcher = make_pitcher("p1")
    swing, contact = ai.decide_swing(
        batter,
        pitcher,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.4,
    )
    assert swing is True
    assert contact == 1.0


def test_pitch_classification():
    cfg = load_config()
    ai = BatterAI(cfg)

    assert ai.pitch_class(0) == "sure strike"
    assert ai.pitch_class(3) == "sure strike"
    assert ai.pitch_class(4) == "close strike"
    assert ai.pitch_class(5) == "close ball"
    assert ai.pitch_class(6) == "sure ball"
