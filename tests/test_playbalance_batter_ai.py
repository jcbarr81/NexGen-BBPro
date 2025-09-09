from playbalance.batter_ai import pitch_identification_chance, discipline_chance
from playbalance.config import PlayBalanceConfig


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
