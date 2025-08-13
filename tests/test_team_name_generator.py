import random
import pytest
from logic.team_name_generator import (
    CITIES,
    MASCOTS,
    random_team,
    reset_name_pool,
)


@pytest.fixture(autouse=True)
def _clear_name_pool():
    """Ensure each test starts with a fresh name pool."""
    reset_name_pool()

def test_random_team_returns_valid_members():
    random.seed(0)
    city, mascot = random_team()
    assert city in CITIES
    assert mascot in MASCOTS

def test_random_team_produces_variety():
    random.seed(1)
    results = {random_team() for _ in range(20)}
    assert len(results) > 1


def test_random_team_unique_until_exhaustion():
    random.seed(2)
    results = {random_team() for _ in range(32)}
    assert len(results) == 32
    with pytest.raises(RuntimeError):
        random_team()
