from playbalance.batter_ai import BatterAI
from tests.util.pbini_factory import make_cfg
from tests.test_simulation import make_player, make_pitcher


def test_close_ball_strike_bias():
    cfg = make_cfg(closeBallStrikeBonus=5, swingProbScale=1.0)
    ai0 = BatterAI(cfg)
    ai2 = BatterAI(cfg)
    batter = make_player("b1")
    pitcher = make_pitcher("p1")

    samples = [i / 1000 for i in range(1000)]
    swings0 = 0
    swings2 = 0
    for rv in samples:
        swing0, _ = ai0.decide_swing(
            batter,
            pitcher,
            pitch_type="fb",
            balls=0,
            strikes=0,
            dist=4,
            random_value=rv,
        )
        swing2, _ = ai2.decide_swing(
            batter,
            pitcher,
            pitch_type="fb",
            balls=0,
            strikes=2,
            dist=4,
            random_value=rv,
        )
        swings0 += int(swing0)
        swings2 += int(swing2)

    assert swings2 > swings0
