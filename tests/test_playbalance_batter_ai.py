from playbalance.batter_ai import (
    BatterAI,
    discipline_chance,
    pitch_identification_chance,
)
from playbalance.config import PlayBalanceConfig
from playbalance.playbalance_config import PlayBalanceConfig as PBPlayBalanceConfig
from tests.test_physics import make_player, make_pitcher


def make_cfg() -> PlayBalanceConfig:
    return PlayBalanceConfig(
        {
            "PlayBalance": {
                "pitchIdBase": 40,
                "pitchIdRatingFactor": 50,
                "pitchIdCountFactor": 10,
                "disciplineBase": 30,
                "disciplineRatingFactor": 40,
                "disciplineBallFactor": 5,
                "disciplineStrikeFactor": 5,
            }
        }
    )


def test_pitch_identification_variation():
    cfg = make_cfg()
    low = pitch_identification_chance(cfg, batter_pi=20, balls=0, strikes=2)
    high = pitch_identification_chance(cfg, batter_pi=80, balls=3, strikes=0)
    assert high > low
    same_rating_low = pitch_identification_chance(cfg, batter_pi=50, balls=0, strikes=2)
    same_rating_high = pitch_identification_chance(cfg, batter_pi=50, balls=3, strikes=0)
    assert same_rating_high > same_rating_low


def test_discipline_variation():
    cfg = make_cfg()
    low = discipline_chance(cfg, batter_dis=20, balls=0, strikes=0)
    high = discipline_chance(cfg, batter_dis=80, balls=0, strikes=0)
    assert high > low
    count_low = discipline_chance(cfg, batter_dis=50, balls=0, strikes=2)
    count_high = discipline_chance(cfg, batter_dis=50, balls=3, strikes=0)
    assert count_high > count_low


def test_discipline_zone_bias_affects_swing():
    cfg = PBPlayBalanceConfig.from_dict({})
    batter_ai = BatterAI(cfg)
    pitcher = make_pitcher("P")
    patient = make_player("PB", ch=80)
    aggressive = make_player("AB", ch=20)

    batter_ai.decide_swing(
        aggressive,
        pitcher,
        "fb",
        balls=0,
        strikes=0,
        dist=int(cfg.sureStrikeDist) or 1,
        random_value=1.0,
    )
    aggressive_rate = batter_ai.last_swing_breakdown["pre_two_strike"]

    batter_ai.decide_swing(
        patient,
        pitcher,
        "fb",
        balls=0,
        strikes=0,
        dist=int(cfg.sureStrikeDist) or 1,
        random_value=1.0,
    )
    patient_rate = batter_ai.last_swing_breakdown["pre_two_strike"]
    assert patient_rate > aggressive_rate


def test_auto_take_probability_triggers(monkeypatch):
    cfg = PBPlayBalanceConfig.from_dict(
        {
            "autoTakeCloseBallBaseProb": 0.9,
            "autoTakeDistanceWeight": 0.4,
        }
    )
    batter_ai = BatterAI(cfg)
    batter = make_player("TA", ch=50)
    pitcher = make_pitcher("TP")
    monkeypatch.setattr("playbalance.batter_ai.random.random", lambda: 0.0)
    swing, _ = batter_ai.decide_swing(
        batter,
        pitcher,
        "fb",
        balls=3,
        strikes=0,
        dist=int(cfg.closeBallDist) + 2,
    )
    assert swing is False


def _estimate_strikeout_rate(ai, batter, pitcher, dist: int) -> float:
    samples = [i / 40 for i in range(40)]
    strikeouts = 0
    for rv in samples:
        swing, _ = ai.decide_swing(
            batter,
            pitcher,
            "fb",
            balls=0,
            strikes=2,
            dist=dist,
            random_value=rv,
            check_random=rv,
        )
        if not swing or not ai.last_contact:
            strikeouts += 1
    return strikeouts / len(samples)


def test_ch_rating_monotonicity():
    cfg = PBPlayBalanceConfig.from_dict({})
    pitcher = make_pitcher("P")
    dist = int(cfg.sureStrikeDist) or 1

    low_ch = make_player("LCH", ch=20)
    high_ch = make_player("HCH", ch=80)

    ai_k = BatterAI(cfg)
    low_k = _estimate_strikeout_rate(ai_k, low_ch, pitcher, dist)
    high_k = _estimate_strikeout_rate(ai_k, high_ch, pitcher, dist)
    assert high_k < low_k

    ai_contact = BatterAI(cfg)
    def _contact_expectation(batter):
        probs = []
        for rv in (i / 10 for i in range(5)):
            ai_contact.decide_swing(
                batter,
                pitcher,
                "fb",
                balls=0,
                strikes=2,
                dist=dist,
                random_value=rv,
                check_random=rv,
            )
            probs.append(ai_contact.last_swing_breakdown["contact_prob"])
        return sum(probs) / len(probs)

    assert _contact_expectation(high_ch) > _contact_expectation(low_ch)
