from __future__ import annotations

"""Helpers for loading and tuning :class:`PlayBalanceConfig`."""

import csv
from typing import Tuple, Dict

from .playbalance_config import PlayBalanceConfig
from utils.path_utils import get_base_dir

# Greater reduction in outs on balls in play to roughly
# triple the rate that balls in play become hits.
# This substantially boosts the simulated BABIP.
_BABIP_OUT_ADJUST = 0.17


def apply_league_benchmarks(
    cfg: PlayBalanceConfig, benchmarks: Dict[str, float]
) -> None:
    """Configure ``cfg`` using league-wide benchmark rates."""

    hr_rate = cfg.hitHRProb / 100
    # Base hit probability derived directly from league BABIP
    cfg.hitProbBase = benchmarks["babip"] / (1 - hr_rate)
    cfg.ballInPlayPitchPct = int(round(benchmarks["pitches_put_in_play_pct"] * 100))
    pitches_per_pa = benchmarks["pitches_per_pa"]
    cfg.swingProbScale = round(4.0 / pitches_per_pa, 2) if pitches_per_pa else 1.0

    # Derive outs on balls in play by type.  Start from MLB-average
    # probabilities and scale them so that the weighted mean matches the
    # league BABIP from the benchmark file.
    gb_pct = benchmarks.get("bip_gb_pct", 0.0)
    fb_pct = benchmarks.get("bip_fb_pct", 0.0)
    ld_pct = benchmarks.get("bip_ld_pct", 0.0)
    babip = benchmarks.get("babip", 0.0)
    base_gb, base_ld, base_fb = 0.76, 0.32, 0.86
    weighted_out = base_gb * gb_pct + base_fb * fb_pct + base_ld * ld_pct
    scale = ((1 - babip) / weighted_out) if weighted_out else 1.0
    scale *= _BABIP_OUT_ADJUST
    cfg.groundOutProb = round(min(max(base_gb * scale, 0.0), 1.0), 3)
    cfg.lineOutProb = round(min(max(base_ld * scale, 0.0), 1.0), 3)
    cfg.flyOutProb = round(min(max(base_fb * scale, 0.0), 1.0), 3)


def load_tuned_playbalance_config() -> Tuple[PlayBalanceConfig, Dict[str, float]]:
    """Return a tuned :class:`PlayBalanceConfig` and MLB averages."""

    base = get_base_dir()
    cfg = PlayBalanceConfig.from_file(base / "logic" / "PBINI.txt")

    csv_path = base / "data" / "MLB_avg" / "mlb_avg_boxscore_2020_2024_both_teams.csv"
    with csv_path.open(newline="") as f:
        row = next(csv.DictReader(f))

    hits = float(row["Hits"])
    singles = hits - float(row["Doubles"]) - float(row["Triples"]) - float(row["HomeRuns"])
    cfg.hit1BProb = int(round(singles / hits * 100))
    cfg.hit2BProb = int(round(float(row["Doubles"]) / hits * 100))
    cfg.hit3BProb = int(round(float(row["Triples"]) / hits * 100))
    cfg.hitHRProb = max(0, 100 - cfg.hit1BProb - cfg.hit2BProb - cfg.hit3BProb)

    bench_path = base / "data" / "MLB_avg" / "mlb_league_benchmarks_2025_filled.csv"
    with bench_path.open(newline="") as bf:
        benchmarks = {r["metric_key"]: float(r["value"]) for r in csv.DictReader(bf)}

    apply_league_benchmarks(cfg, benchmarks)
    mlb_averages = {stat: float(val) for stat, val in row.items() if stat}
    return cfg, mlb_averages
