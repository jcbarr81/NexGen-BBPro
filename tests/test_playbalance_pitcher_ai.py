import random
from types import SimpleNamespace

import pytest

from playbalance.pitcher_ai import (
    pitch_rating_variation,
    objective_weights_by_count,
    select_pitch,
    apply_selection_adjustments,
)


class ConstRandom(random.Random):
    """Random generator returning a constant ``value`` from ``random``."""

    def __init__(self, value: float):
        super().__init__()
        self.value = value

    def random(self) -> float:  # type: ignore[override]
        return self.value


def test_pitch_rating_variation():
    cfg = SimpleNamespace(pitchRatingVariationPct=10)
    high = pitch_rating_variation(cfg, 50, ConstRandom(1.0))
    low = pitch_rating_variation(cfg, 50, ConstRandom(0.0))
    assert high == pytest.approx(55.0)
    assert low == pytest.approx(45.0)


def test_pitch_rating_variation_clamped():
    cfg = SimpleNamespace(pitchRatingVariationPct=10)
    high = pitch_rating_variation(cfg, 100, ConstRandom(1.0))
    low = pitch_rating_variation(cfg, 0, ConstRandom(0.0))
    assert high == 100.0
    assert low == 0.0


def test_selection_adjustment_changes_choice():
    cfg = SimpleNamespace(pitchRatingVariationPct=0, pitchSelectionAdjust={"fb": 15})
    pitch_ratings = {"fb": 50, "sl": 60}
    pitch, loc = select_pitch(cfg, pitch_ratings, rng=ConstRandom(0.5))
    assert pitch == "fb"
    assert loc == "zone"  # default objective


def test_objective_weights_determine_location():
    cfg = SimpleNamespace(
        pitchRatingVariationPct=0,
        pitchObjectiveWeights={"0-0": {"attack": 1.0, "chase": 2.0, "waste": 0.0}},
    )
    weights = objective_weights_by_count(cfg, 0, 0)
    assert weights["chase"] == 2.0
    pitch, loc = select_pitch(cfg, {"fb": 50}, balls=0, strikes=0, rng=ConstRandom(0.5))
    assert pitch == "fb"
    assert loc == "edge"


def test_objective_weights_random_choice():
    cfg = SimpleNamespace(
        pitchRatingVariationPct=0,
        pitchObjectiveWeights={"0-0": {"attack": 1.0, "chase": 1.0}},
    )
    pitch_ratings = {"fb": 50}
    pitch, loc = select_pitch(cfg, pitch_ratings, balls=0, strikes=0, rng=ConstRandom(0.0))
    assert loc == "zone"
    pitch, loc = select_pitch(cfg, pitch_ratings, balls=0, strikes=0, rng=ConstRandom(0.9))
    assert loc == "edge"


def test_apply_selection_adjustments():
    ratings = {"fb": 50, "sl": 60}
    adj = apply_selection_adjustments(ratings, {"fb": 10})
    assert adj["fb"] == 60.0 and adj["sl"] == 60.0

