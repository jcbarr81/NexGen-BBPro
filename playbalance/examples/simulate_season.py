"""Example script running a small season simulation."""
from playbalance.config import load_config
from playbalance.benchmarks import load_benchmarks
from playbalance.orchestrator import simulate_season


def main() -> None:
    cfg = load_config()
    benchmarks = load_benchmarks()
    stats = simulate_season(cfg, benchmarks, games=20, rng_seed=0)
    print(stats.as_dict())


if __name__ == "__main__":  # pragma: no cover - example usage
    main()
