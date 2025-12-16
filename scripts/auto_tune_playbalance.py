#!/usr/bin/env python3
"""Small step-by-step solver that nudges key play-balance settings."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from playbalance.sim_config import load_tuned_playbalance_config


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class TuningRule:
    """Mapping from a metric delta to a configuration adjustment."""

    key: str
    metric: str
    sensitivity: float
    clamp_min: float
    clamp_max: float
    inverse: bool = True
    tolerance: float = 0.001
    integer: bool = False
    digits: int = 3

    def apply(
        self,
        metrics: Mapping[str, float | None],
        benchmarks: Mapping[str, float | None],
        current_value: float | int,
    ) -> tuple[float | int, float]:
        metric_value = metrics.get(self.metric)
        target_value = benchmarks.get(self.metric)
        if metric_value is None or target_value is None:
            return current_value, 0.0
        diff = metric_value - target_value
        if abs(diff) < self.tolerance:
            return current_value, 0.0
        delta = (-diff if self.inverse else diff) * self.sensitivity
        new_value = _clamp(float(current_value) + delta, self.clamp_min, self.clamp_max)
        if self.integer:
            new_value = int(round(new_value))
        else:
            new_value = round(new_value, self.digits)
        if new_value == current_value:
            return current_value, 0.0
        return new_value, float(new_value) - float(current_value)


TUNING_RULES: tuple[TuningRule, ...] = (
    TuningRule("swingProbScale", "swing_pct", sensitivity=0.45, clamp_min=0.6, clamp_max=1.6),
    TuningRule("zSwingProbScale", "z_swing_pct", sensitivity=0.4, clamp_min=0.5, clamp_max=1.6),
    TuningRule("oSwingProbScale", "o_swing_pct", sensitivity=0.4, clamp_min=0.6, clamp_max=2.0),
    TuningRule(
        "ballInPlayPitchPct",
        "pitches_put_in_play_pct",
        sensitivity=40.0,
        clamp_min=1,
        clamp_max=80,
        integer=True,
        digits=0,
    ),
    TuningRule(
        "pitchAroundChanceBase",
        "bb_pct",
        sensitivity=160.0,
        clamp_min=-40,
        clamp_max=80,
        integer=True,
        digits=0,
    ),
    TuningRule(
        "pitchAroundChanceOn23",
        "bb_pct",
        sensitivity=80.0,
        clamp_min=-40,
        clamp_max=80,
        integer=True,
        digits=0,
    ),
)


def apply_tuning_rules(
    metrics: Mapping[str, float | None],
    benchmarks: Mapping[str, float | None],
    values: Mapping[str, float | int | None],
    rules: Iterable[TuningRule] = TUNING_RULES,
) -> Dict[str, float | int]:
    """Return adjusted configuration values based on metric deltas."""

    updates: Dict[str, float | int] = {}
    for rule in rules:
        current_value = values.get(rule.key)
        if current_value is None:
            continue
        new_value, delta = rule.apply(metrics, benchmarks, current_value)
        if delta != 0.0:
            updates[rule.key] = new_value
    return updates


def _load_results(path: Path) -> tuple[dict[str, float | None], dict[str, float | None]]:
    data = json.loads(path.read_text())
    metrics = data.get("metrics", {})
    benchmarks = data.get("benchmarks", {})
    return metrics, benchmarks


def _load_overrides(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Automatically nudge play-balance knobs based on sim results"
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("results.json"),
        help="path to aggregated sim metrics JSON (default: results.json)",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=Path("data/playbalance_overrides.json"),
        help="play-balance overrides file to update",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="persist the adjustments back to the overrides file",
    )
    args = parser.parse_args(argv)

    metrics, benchmarks = _load_results(args.results)
    overrides = _load_overrides(args.overrides)
    cfg, _ = load_tuned_playbalance_config(apply_benchmarks=True)
    values_snapshot: Dict[str, float | int | None] = {}
    for rule in TUNING_RULES:
        values_snapshot[rule.key] = overrides.get(rule.key, getattr(cfg, rule.key, None))

    adjustments = apply_tuning_rules(metrics, benchmarks, values_snapshot)
    if not adjustments:
        print("All monitored metrics are within tolerance; no updates required.")
        return 0

    print("Suggested adjustments:")
    for key, new_value in adjustments.items():
        old_value = values_snapshot.get(key)
        print(f"  - {key}: {old_value} -> {new_value}")
        overrides[key] = new_value

    if args.write:
        args.overrides.write_text(json.dumps(overrides, indent=2))
        print(f"Wrote {len(adjustments)} updates to {args.overrides}")
    else:
        print("Re-run with --write to persist these overrides.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
