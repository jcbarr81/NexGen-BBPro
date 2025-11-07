from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PitchSurvivalTracker:
    """Track plate-appearance pitch counts and derive survival curves."""

    pitch_counts: Counter[int] = field(default_factory=Counter)
    total_plate_appearances: int = 0

    def record_plate(self, pitches: int) -> None:
        """Record a completed plate appearance with ``pitches`` pitches."""

        if pitches <= 0:
            return
        self.pitch_counts[pitches] += 1
        self.total_plate_appearances += 1

    # ------------------------------------------------------------------ #
    # Derived metrics
    # ------------------------------------------------------------------ #
    def mean_pitches(self) -> float:
        if not self.total_plate_appearances:
            return 0.0
        total = sum(length * count for length, count in self.pitch_counts.items())
        return total / self.total_plate_appearances

    def percentile(self, pct: float) -> float:
        """Return the pitch-count percentile (0..1)."""

        if not self.total_plate_appearances:
            return 0.0
        target = max(0.0, min(1.0, pct)) * (self.total_plate_appearances - 1)
        cumulative = 0
        for length in sorted(self.pitch_counts):
            cumulative += self.pitch_counts[length]
            if cumulative > target:
                return float(length)
        return float(max(self.pitch_counts))

    def distribution(self) -> Dict[int, int]:
        """Return a sorted copy of the pitch-count histogram."""

        return dict(sorted(self.pitch_counts.items()))

    def survival_curve(self) -> List[Dict[str, float]]:
        """Return survival probabilities after each pitch."""

        total = self.total_plate_appearances
        if not total:
            return []
        max_len = max(self.pitch_counts)
        remaining = total
        curve: List[Dict[str, float]] = []
        for pitch in range(1, max_len + 1):
            alive = remaining / total
            resolved = self.pitch_counts.get(pitch, 0)
            curve.append(
                {
                    "pitch": pitch,
                    "alive": alive,
                    "resolved": resolved / total,
                }
            )
            remaining -= resolved
            if remaining <= 0:
                break
        return curve

    def metrics(self) -> Dict[str, float]:
        """Return summary metrics for quick inspection."""

        return {
            "plate_appearances": self.total_plate_appearances,
            "mean_pitches": self.mean_pitches(),
            "median_pitches": self.percentile(0.5),
            "p90_pitches": self.percentile(0.9),
            "max_pitches": max(self.pitch_counts) if self.pitch_counts else 0,
        }


__all__ = ["PitchSurvivalTracker"]
