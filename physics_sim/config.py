from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import json


DEFAULT_TUNING: Dict[str, float] = {
    # Global run environment
    "offense_scale": 1.0,
    "pitching_dom_scale": 1.0,
    # Plate discipline / swing behaviour
    "zone_swing_scale": 1.0,
    "chase_scale": 1.0,
    "two_strike_aggression_scale": 1.0,
    "eye_scale": 1.0,
    # Outcomes
    "hr_scale": 1.0,
    "babip_scale": 1.0,
    "walk_scale": 1.0,
    "k_scale": 1.0,
    "contact_quality_scale": 1.0,
    # Pitch/command
    "velocity_scale": 1.0,
    "movement_scale": 1.0,
    "command_variance_scale": 1.0,
    "fatigue_decay_scale": 1.0,
    # Park/environment
    "park_size_scale": 1.0,
    "foul_territory_scale": 1.0,
    "wind_speed": 0.0,
    "wind_angle_deg": 0.0,
    "altitude_scale": 1.0,
    # Fielding / baserunning
    "range_scale": 1.0,
    "arm_strength_scale": 1.0,
    "error_rate_scale": 1.0,
    "speed_scale": 1.0,
    "steal_freq_scale": 1.0,
    "advancement_aggression_scale": 1.0,
    # Batted-ball shape
    "gb_fb_tilt": 1.0,
}


@dataclass
class TuningConfig:
    """Container for all user-adjustable tuning knobs."""

    values: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_TUNING))

    @classmethod
    def from_overrides(
        cls,
        *,
        overrides: Optional[Dict[str, Any]] = None,
        overrides_path: Optional[Path] = None,
    ) -> "TuningConfig":
        base = dict(DEFAULT_TUNING)
        data: Dict[str, Any] = {}
        if overrides_path:
            try:
                with Path(overrides_path).open("r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        data.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
        if overrides:
            data.update(overrides)
        for k, v in data.items():
            if k in base:
                try:
                    base[k] = float(v)
                except (TypeError, ValueError):
                    continue
        return cls(values=base)

    def get(self, key: str, default: Optional[float] = None) -> float:
        return float(self.values.get(key, default if default is not None else 0.0))


def load_tuning(
    overrides: Optional[Dict[str, Any]] = None, overrides_path: Optional[Path] = None
) -> TuningConfig:
    """Load a :class:`TuningConfig` merging optional overrides."""

    return TuningConfig.from_overrides(overrides=overrides, overrides_path=overrides_path)
