from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable

from .config import TuningConfig
from .models import PitcherRatings


@dataclass
class PitcherWorkload:
    fatigue_debt: float = 0.0
    last_used_day: int | None = None
    consecutive_days_used: int = 0
    last_update_day: int | None = None


@dataclass
class UsageState:
    current_day: int | None = None
    workloads: Dict[str, PitcherWorkload] = field(default_factory=dict)

    def workload_for(self, pitcher_id: str) -> PitcherWorkload:
        if pitcher_id not in self.workloads:
            self.workloads[pitcher_id] = PitcherWorkload()
        return self.workloads[pitcher_id]

    def advance_day(
        self,
        *,
        day: int,
        pitchers: Iterable[PitcherRatings],
        tuning: TuningConfig,
    ) -> None:
        if self.current_day is None:
            self.current_day = day
        if day < self.current_day:
            return
        days_passed = day - self.current_day
        if days_passed <= 0:
            for pitcher in pitchers:
                workload = self.workload_for(pitcher.player_id)
                if workload.last_update_day is None:
                    workload.last_update_day = day
            return

        base = tuning.get("daily_recovery_base", 20.0)
        scale = tuning.get("daily_recovery_durability_scale", 0.4)
        for pitcher in pitchers:
            workload = self.workload_for(pitcher.player_id)
            recovery = days_passed * (base + pitcher.durability * scale)
            workload.fatigue_debt = max(0.0, workload.fatigue_debt - recovery)
            workload.last_update_day = day
            if workload.last_used_day is not None and day - workload.last_used_day > 1:
                workload.consecutive_days_used = 0

        self.current_day = day

    def record_outing(
        self,
        *,
        pitcher_id: str,
        pitches: int,
        day: int,
        multiplier: float,
        tuning: TuningConfig,
    ) -> None:
        workload = self.workload_for(pitcher_id)
        debt_scale = tuning.get("fatigue_debt_scale", 1.0)
        workload.fatigue_debt += pitches * debt_scale * multiplier
        if workload.last_used_day is not None and day - workload.last_used_day == 1:
            workload.consecutive_days_used += 1
        else:
            workload.consecutive_days_used = 1
        workload.last_used_day = day
        penalty = tuning.get("consecutive_usage_penalty", 8.0)
        if workload.consecutive_days_used > 1:
            workload.fatigue_debt += penalty * (workload.consecutive_days_used - 1)
