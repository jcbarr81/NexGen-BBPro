import random

from playbalance.season_simulator import SeasonSimulator


def test_simulate_regular_season_to_completion():
    schedule = [
        {"date": "2024-04-01", "home": "A", "away": "B"},
        {"date": "2024-05-01", "home": "C", "away": "D"},
        {"date": "2024-06-01", "home": "E", "away": "F"},
    ]
    played = []

    sim = SeasonSimulator(schedule, simulate_game=lambda h, a: played.append((h, a)))

    for _ in range(len({g["date"] for g in schedule})):
        sim.simulate_next_day()

    assert len(played) == len(schedule)
    sim.simulate_next_day()
    assert len(played) == len(schedule)


def test_default_simulation_runs_without_callback():
    """Ensure the built-in season simulation runs using full game playbalance."""
    schedule = [{"date": "2024-04-01", "home": "DRO", "away": "CEA"}]

    sim = SeasonSimulator(schedule)

    # Should execute without raising exceptions using real roster data
    sim.simulate_next_day()


def _random_game(home: str, away: str, seed: int | None = None):
    rng = random.Random(seed)
    return rng.randint(0, 10), rng.randint(0, 10)


def test_parallel_simulation_invokes_after_game():
    schedule = [
        {"date": "2024-04-01", "home": "A", "away": "B"},
        {"date": "2024-04-01", "home": "C", "away": "D"},
    ]
    recorded: list[str] = []

    sim = SeasonSimulator(schedule, simulate_game=_random_game, after_game=lambda g: recorded.append(g["result"]))

    sim.simulate_next_day()

    assert len(recorded) == 2
    assert all("result" in g for g in schedule)
