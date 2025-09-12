from playbalance.fielding_ai import FieldingAI
from tests.util.pbini_factory import make_cfg


def test_glove_side_vs_cross_body_probability():
    cfg = make_cfg(
        wildCatchChanceBase=80,
        wildCatchChanceFAPct=50,
        wildCatchChanceOppMod=-20,
    )
    ai = FieldingAI(cfg)
    fa = 60
    glove = ai.wild_pitch_catch_probability(fa, glove_side=True, high=False)
    cross = ai.wild_pitch_catch_probability(fa, glove_side=False, high=False)
    expected_glove = min(1.0, (80 + 50 * fa / 100) / 100)
    expected_cross = min(1.0, (80 + 50 * fa / 100 - 20) / 100)
    assert glove == expected_glove
    assert cross == expected_cross
    assert cross < glove

