from logic.season_simulator import SeasonSimulator


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
    """Ensure the built-in placeholder game simulation runs without error."""
    schedule = [{"date": "2024-04-01", "home": "A", "away": "B"}]

    sim = SeasonSimulator(schedule)

    # Should not raise any exceptions even though player data is minimal
    sim.simulate_next_day()
