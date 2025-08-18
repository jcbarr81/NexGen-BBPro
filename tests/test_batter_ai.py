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
    cfg.values.update(
        {
            "idRatingBase": 0,
            "idRatingCHPct": 0,
            "idRatingExpPct": 0,
            "idRatingPitchRatPct": 0,
        }
    )
    ai = BatterAI(cfg)
    batter = make_player("b1")
    batter.ch = 0
    batter.exp = 0
    pitcher = make_pitcher("p1")
    pitcher.fb = 100
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
    cfg.values.update(
        {
            "idRatingBase": 0,
            "idRatingCHPct": 0,
            "idRatingExpPct": 0,
            "idRatingPitchRatPct": 0,
            "lookPrimaryType00CountAdjust": 50,
        }
    )
    ai = BatterAI(cfg)
    batter = make_player("b1")
    batter.ch = 0
    batter.exp = 0
    pitcher = make_pitcher("p1")
    pitcher.fb = 100
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


def test_best_look_adjust_increases_swings():
    cfg = load_config()
    cfg.values.update(
        {
            "idRatingBase": 0,
            "idRatingCHPct": 0,
            "idRatingExpPct": 0,
            "idRatingPitchRatPct": 0,
            "lookBestType00CountAdjust": 50,
        }
    )
    ai = BatterAI(cfg)
    batter = make_player("b1")
    batter.ch = 0
    batter.exp = 0
    pitcher = make_pitcher("p1")
    pitcher.fb = 100
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


def test_ch_and_exp_ratings_increase_identification():
    cfg = load_config()
    cfg.values.update({"idRatingBase": 0, "idRatingPitchRatPct": 0})
    ai = BatterAI(cfg)
    pitcher = make_pitcher("p1")
    pitcher.fb = 100

    batter_low = make_player("low")
    batter_low.ch = 0
    batter_low.exp = 0
    swing_low, contact_low = ai.decide_swing(
        batter_low,
        pitcher,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.4,
    )

    batter_high = make_player("high")
    batter_high.ch = 100
    batter_high.exp = 100
    swing_high, contact_high = ai.decide_swing(
        batter_high,
        pitcher,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.4,
    )

    assert swing_low is True
    assert contact_low == 0.5
    assert swing_high is True
    assert contact_high == 1.0


def test_pitch_rating_makes_identification_harder():
    cfg = load_config()
    cfg.values.update(
        {
            "idRatingBase": 0,
            "idRatingCHPct": 0,
            "idRatingExpPct": 0,
            "idRatingPitchRatPct": 100,
        }
    )
    ai = BatterAI(cfg)
    batter = make_player("b1")
    batter.ch = 0
    batter.exp = 0

    pitcher_easy = make_pitcher("easy")
    pitcher_easy.fb = 0
    swing_e, contact_e = ai.decide_swing(
        batter,
        pitcher_easy,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.4,
    )

    pitcher_hard = make_pitcher("hard")
    pitcher_hard.fb = 100
    swing_h, contact_h = ai.decide_swing(
        batter,
        pitcher_hard,
        pitch_type="fb",
        balls=0,
        strikes=0,
        dist=0,
        random_value=0.4,
    )

    assert swing_e is True and contact_e == 1.0
    assert swing_h is True and contact_h == 0.5


def test_pitch_classification():
    cfg = load_config()
    ai = BatterAI(cfg)

    assert ai.pitch_class(0) == "sure strike"
    assert ai.pitch_class(3) == "sure strike"
    assert ai.pitch_class(4) == "close strike"
    assert ai.pitch_class(5) == "close ball"
    assert ai.pitch_class(6) == "sure ball"
