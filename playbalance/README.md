# Play-Balance Simulation Engine

This package provides a light-weight reimplementation of the classic
`PBINI` formulas used in the original Baseball Pro series.  Modules expose
small, well-tested helpers for tactics and physics and are combined by the
`orchestrator` module into a very small game loop.

## Running simulations

The orchestrator can be executed directly to simulate one or more games:

```bash
python -m playbalance.orchestrator --games 10 --seed 0
```

The script prints game averages alongside the MLB league benchmarks loaded
from `data/MLB_avg/mlb_league_benchmarks_2025_filled.csv`.

The orchestrator also exposes helpers that can be wired to the season progress
menu or UI:

```python
from playbalance.config import load_config
from playbalance.benchmarks import load_benchmarks
from playbalance.orchestrator import simulate_day, simulate_week

cfg = load_config()
benchmarks = load_benchmarks()

# Simulate a single day and a full week of games
simulate_day(cfg, benchmarks)
simulate_week(cfg, benchmarks)
```

See `examples/simulate_season.py` for a complete example script.

## Benchmark metrics

The benchmark CSV contains league-wide averages used to calibrate the engine.
The orchestrator focuses on a handful of key metrics:

| Metric | Description |
|--------|-------------|
| `k_pct` | Strikeouts per plate appearance |
| `bb_pct` | Walks per plate appearance |
| `babip` | Batting average on balls in play |
| `sba_per_pa` | Stolen-base attempts per plate appearance |
| `sb_pct` | Stolen-base success percentage |

These values are returned by `playbalance.benchmarks.league_average`.

## Testing

Integration tests in `tests/test_playbalance_orchestrator.py` simulate short
seasons and verify that the aggregated statistics stay within tolerance of
the benchmark targets.
