import os
import random


def pytest_sessionstart(session):
    """Ensure a non-deterministic RNG for tests depending on randomness."""
    random.seed()
    os.environ.setdefault("PB_DISABLE_ROLLOVER", "1")
