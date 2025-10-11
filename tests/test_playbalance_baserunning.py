from types import SimpleNamespace
from random import Random

from playbalance import lead_level, pickoff_scare


class ConstRandom(Random):
    """Random generator returning a constant value from ``random``."""

    def __init__(self, value: float):
        super().__init__()
        self.value = value

    def random(self) -> float:  # type: ignore[override]
        return self.value


def test_long_lead_threshold():
    cfg = SimpleNamespace(longLeadSpeed=60)
    assert lead_level(cfg, 70) == 2
    assert lead_level(cfg, 59) == 0


def test_pickoff_scare_behavior():
    cfg = SimpleNamespace(pickoffScareSpeed=60)
    # Slow runner can be scared back on low roll
    scared = pickoff_scare(cfg, 50, 2, rng=ConstRandom(0.05))
    assert scared == 0
    # Fast runner ignores scare
    not_scared = pickoff_scare(cfg, 80, 2, rng=ConstRandom(0.05))
    assert not_scared == 2
    # Slow runner with high roll stays aggressive
    no_event = pickoff_scare(cfg, 50, 2, rng=ConstRandom(0.2))
    assert no_event == 2
