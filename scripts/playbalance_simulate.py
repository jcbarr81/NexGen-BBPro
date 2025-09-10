"""Run play-balance simulations for common time spans.

This script loads the real application rosters and players before executing
the pitch-by-pitch play-balance engine.  Results from the simulation are
written to a JSON file containing aggregated statistics such as strikeouts,
walks and pitches thrown.

Usage examples::

    python scripts/playbalance_simulate.py day
    python scripts/playbalance_simulate.py week --seed 1
    python scripts/playbalance_simulate.py season --games 20 --output results.json

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playbalance.benchmarks import load_benchmarks, league_average
from playbalance.config import load_config
from playbalance.orchestrator import (
    simulate_day,
    simulate_week,
    simulate_month,
    simulate_season,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Simulate games using the play-balance engine"
    )
    parser.add_argument(
        "period",
        choices=["day", "week", "month", "season"],
        help="length of simulation to run",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=162,
        help="number of games for a full season simulation",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="random seed for reproducibility"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional file to write JSON results to",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    benchmarks = load_benchmarks()

    if args.period == "day":
        result = simulate_day(cfg, benchmarks, rng_seed=args.seed)
    elif args.period == "week":
        result = simulate_week(cfg, benchmarks, rng_seed=args.seed)
    elif args.period == "month":
        result = simulate_month(cfg, benchmarks, rng_seed=args.seed)
    else:
        result = simulate_season(
            cfg, benchmarks, games=args.games, rng_seed=args.seed
        )

    data = result.as_dict()
    output_path = args.output or Path(f"playbalance_{args.period}_results.json")
    output_path.write_text(json.dumps(data, indent=2))
    print(f"Saved results to {output_path}")

    if args.period == "season":
        pa = result.pa or 1
        k_pct = result.k / pa
        bb_pct = result.bb / pa
        babip = result.hits / result.bip if result.bip else 0.0
        sba_rate = result.sb_attempts / pa
        sb_pct = result.sb_success / result.sb_attempts if result.sb_attempts else 0.0

        print("Simulated Games:", args.games)
        print(
            f"K%:  {k_pct:.3f} "
            f"(MLB {league_average(benchmarks, 'k_pct'):.3f})"
        )
        print(
            f"BB%: {bb_pct:.3f} "
            f"(MLB {league_average(benchmarks, 'bb_pct'):.3f})"
        )
        print(
            f"BABIP: {babip:.3f} "
            f"(MLB {league_average(benchmarks, 'babip'):.3f})"
        )
        print(
            "SB Attempt/PA: "
            f"{sba_rate:.3f} (MLB {league_average(benchmarks, 'sba_per_pa'):.3f})"
        )
        print(
            f"SB%: {sb_pct:.3f} "
            f"(MLB {league_average(benchmarks, 'sb_pct'):.3f})"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())

