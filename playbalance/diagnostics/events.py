from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class SwingDecisionEvent:
    """Outcome of a swing/take decision for a single pitch."""

    swing: bool
    contact: bool
    foul: bool
    ball_in_play: bool
    hit: bool
    ball: bool
    called_strike: bool
    walk: bool
    strikeout: bool
    hbp: bool
    contact_quality: Optional[float] = None
    result: Optional[str] = None
    auto_take: bool = False
    auto_take_reason: Optional[str] = None
    auto_take_threshold: Optional[float] = None
    auto_take_distance: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PitchEvent:
    """Captures a single pitch with context and decision outcome."""

    inning: int
    half: str
    batter_id: str
    pitcher_id: str
    balls: int
    strikes: int
    pitch_type: str
    objective: str
    target_offset: Optional[tuple[float, float]] = None
    in_zone: bool = False
    pitch_distance: Optional[float] = None
    pitch_dx: Optional[float] = None
    pitch_dy: Optional[float] = None
    pitch_speed: Optional[float] = None
    decision: SwingDecisionEvent | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.decision is not None:
            data["decision"] = self.decision.to_dict()
        return data


@dataclass
class PlateAppearanceEvent:
    """Stores a full plate appearance worth of pitch events."""

    inning: int
    half: str
    batter_id: str
    pitcher_id: str
    pitches: List[PitchEvent] = field(default_factory=list)
    result: Optional[str] = None
    outs_recorded: int = 0
    runs_scored: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["pitches"] = [p.to_dict() for p in self.pitches]
        return data


class DiagnosticsRecorder:
    """Collects pitch/PA events and optionally emits JSON lines."""

    def __init__(self, emit_path: str | Path | None = None) -> None:
        self.emit_path = Path(emit_path) if emit_path else None
        self.plate_appearances: List[PlateAppearanceEvent] = []
        self._current_pa: PlateAppearanceEvent | None = None
        if self.emit_path is not None:
            self.emit_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Plate appearance lifecycle
    # ------------------------------------------------------------------ #
    def start_plate_appearance(self, pa: PlateAppearanceEvent) -> None:
        self._current_pa = pa

    def finish_plate_appearance(self, *, result: str, outs: int, runs_scored: int = 0) -> None:
        if self._current_pa is None:
            return
        self._current_pa.result = result
        self._current_pa.outs_recorded = outs
        self._current_pa.runs_scored = runs_scored
        self.plate_appearances.append(self._current_pa)
        if self.emit_path is not None:
            self._write_line(self._current_pa.to_dict())
        self._current_pa = None

    # ------------------------------------------------------------------ #
    # Pitch logging
    # ------------------------------------------------------------------ #
    def record_pitch(self, event: PitchEvent) -> None:
        if self._current_pa is not None:
            self._current_pa.pitches.append(event)
        if self.emit_path is not None:
            self._write_line(event.to_dict())

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def iter_plate_appearances(self) -> Iterable[PlateAppearanceEvent]:
        yield from self.plate_appearances

    def _write_line(self, payload: dict) -> None:
        if self.emit_path is None:
            return
        with self.emit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload))
            fh.write("\n")


__all__ = [
    "DiagnosticsRecorder",
    "PitchEvent",
    "PlateAppearanceEvent",
    "SwingDecisionEvent",
]
