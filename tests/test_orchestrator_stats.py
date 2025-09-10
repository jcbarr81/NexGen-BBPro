from playbalance.orchestrator import simulate_games
from playbalance.benchmarks import load_benchmarks, league_average


def test_simulation_results_reasonable():
    benchmarks = load_benchmarks()
    stats = simulate_games(10, rng_seed=1)
    pa = stats.pa or 1
    bb_pct = stats.bb / pa
    k_pct = stats.k / pa
    assert abs(bb_pct - league_average(benchmarks, "bb_pct")) < 0.1
    assert abs(k_pct - league_average(benchmarks, "k_pct")) < 0.1
