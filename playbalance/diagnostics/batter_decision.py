from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple


CountKey = Tuple[int, int]


@dataclass
class BatterDecisionTracker:
    """Accumulates batter decision metrics keyed by count."""

    totals: Dict[CountKey, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )
    breakdown_totals: Dict[CountKey, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )
    breakdown_counts: Dict[CountKey, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    pitch_kind_counts: Dict[CountKey, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    objective_counts: Dict[CountKey, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    target_offset_totals: Dict[CountKey, list[float]] = field(
        default_factory=lambda: defaultdict(lambda: [0.0, 0.0])
    )
    target_offset_counts: Dict[CountKey, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    total_pitches: int = 0

    def record(
        self,
        *,
        balls: int,
        strikes: int,
        in_zone: bool,
        swing: bool,
        contact: bool,
        foul: bool,
        ball_in_play: bool,
        hit: bool,
        ball: bool,
        called_strike: bool,
        walk: bool,
        strikeout: bool,
        hbp: bool,
        breakdown: Dict[str, float | str] | None = None,
        objective: str | None = None,
        target_offset: Tuple[float, float] | None = None,
    ) -> None:
        """Record a single pitch decision."""

        key = (balls, strikes)
        bucket = self.totals[key]

        bucket["pitches"] += 1
        bucket["swings"] += 1 if swing else 0
        bucket["takes"] += 1 if not swing else 0
        bucket["contact"] += 1 if contact else 0
        bucket["foul"] += 1 if foul else 0
        bucket["ball_in_play"] += 1 if ball_in_play else 0
        bucket["hits"] += 1 if hit else 0
        bucket["balls"] += 1 if ball else 0
        bucket["called_strikes"] += 1 if called_strike else 0
        bucket["walks"] += 1 if walk else 0
        bucket["strikeouts"] += 1 if strikeout else 0
        bucket["hbp"] += 1 if hbp else 0
        bucket["zone_pitches"] += 1 if in_zone else 0

        if objective:
            self.objective_counts[key][objective] += 1
        if target_offset is not None:
            totals = self.target_offset_totals[key]
            totals[0] += float(target_offset[0])
            totals[1] += float(target_offset[1])
            self.target_offset_counts[key] += 1

        self.total_pitches += 1
        if breakdown:
            self.breakdown_counts[key] += 1
            bd_bucket = self.breakdown_totals[key]
            for comp, value in breakdown.items():
                if isinstance(value, (int, float)):
                    bd_bucket[comp] += float(value)
                elif comp == "pitch_kind":
                    pitch_bucket = self.pitch_kind_counts[key]
                    pitch_bucket[str(value)] += 1
                # Ignore non-numeric components apart from pitch kind.

    # ------------------------------------------------------------------ #
    # Convenience accessors
    # ------------------------------------------------------------------ #

    def iter_rows(self) -> Iterable[Tuple[int, int, Dict[str, float]]]:
        for (balls, strikes), stats in sorted(self.totals.items()):
            yield balls, strikes, stats

    def iter_breakdown_rows(
        self,
    ) -> Iterable[Tuple[int, int, int, Dict[str, float], Dict[str, int]]]:
        for (balls, strikes), count in sorted(self.breakdown_counts.items()):
            totals = self.breakdown_totals.get((balls, strikes), {})
            averages = {key: value / count for key, value in totals.items()}
            pitch_counts = dict(self.pitch_kind_counts.get((balls, strikes), {}))
            yield balls, strikes, count, averages, pitch_counts
