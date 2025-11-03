from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple


BucketKey = Tuple[int, int, str]
ObjectiveKey = Tuple[int, int, str]
PitchKey = Tuple[int, int, str, str]


_OBJECTIVE_BUCKET_MAP: Dict[str, str] = {
    # Treat ``outside`` as waste/nibble; remaining objectives are zone-focused.
    "outside": "waste",
    "establish": "zone",
    "best": "zone",
    "best_center": "zone",
    "fast_center": "zone",
    "plus": "zone",
}


def bucket_for_objective(objective: str) -> str:
    """Return aggregate bucket label for an objective."""

    return _OBJECTIVE_BUCKET_MAP.get(objective.lower(), "zone")


@dataclass
class PitchIntentTracker:
    """Accumulate pitch intent counts for diagnostics."""

    bucket_counts: Counter[BucketKey] = field(default_factory=Counter)
    objective_counts: Counter[ObjectiveKey] = field(default_factory=Counter)
    pitch_counts: Counter[PitchKey] = field(default_factory=Counter)
    total: int = 0

    def record(
        self,
        *,
        balls: int,
        strikes: int,
        objective: str,
        pitch_type: str,
        pitcher_id: str | None = None,
    ) -> None:
        """Record a pitch selection."""

        bucket = bucket_for_objective(objective)
        key = (balls, strikes, bucket)
        self.bucket_counts[key] += 1
        self.objective_counts[(balls, strikes, objective)] += 1
        self.pitch_counts[(balls, strikes, bucket, pitch_type)] += 1
        self.total += 1

    # ------------------------------------------------------------------ #
    # Convenience accessors
    # ------------------------------------------------------------------ #

    def bucket_matrix(self, bucket: str) -> Dict[Tuple[int, int], int]:
        """Return count matrix for ``bucket`` keyed by (balls, strikes)."""

        return {
            (balls, strikes): count
            for (balls, strikes, b), count in self.bucket_counts.items()
            if b == bucket
        }

    def iter_bucket_rows(self) -> Iterable[Tuple[int, int, str, int]]:
        """Yield raw rows ``(balls, strikes, bucket, count)`` for CSV export."""

        for (balls, strikes, bucket), count in self.bucket_counts.items():
            yield balls, strikes, bucket, count

    def iter_objective_rows(self) -> Iterable[Tuple[int, int, str, int]]:
        """Yield raw rows ``(balls, strikes, objective, count)`` for CSV."""

        for (balls, strikes, objective), count in self.objective_counts.items():
            yield balls, strikes, objective, count

    def percentage_by_bucket(self) -> Dict[str, float]:
        """Return overall share per bucket."""

        totals: Dict[str, int] = defaultdict(int)
        for (_, _, bucket), count in self.bucket_counts.items():
            totals[bucket] += count
        return {
            bucket: (count / self.total) if self.total else 0.0
            for bucket, count in totals.items()
        }

