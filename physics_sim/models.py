from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


PITCH_KEYS = ["fb", "sl", "si", "cb", "cu", "scb", "kn"]


@dataclass
class BatterRatings:
    player_id: str
    bats: str
    primary_position: str
    other_positions: List[str]
    contact: float  # CH
    power: float  # PH
    gb_tendency: float  # GF
    pull_tendency: float  # PL
    vs_left: float  # VL
    fielding: float  # FA
    arm: float  # ARM
    speed: float  # SP
    durability: float

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "BatterRatings":
        def f(key: str, default: float = 50.0) -> float:
            try:
                return float(row.get(key, default))
            except (TypeError, ValueError):
                return default

        other_positions = [
            p.strip()
            for p in (row.get("other_positions") or "").split(",")
            if p.strip()
        ]
        return cls(
            player_id=str(row.get("player_id", "")),
            bats=str(row.get("bats", "") or "R").upper(),
            primary_position=str(row.get("primary_position", "") or ""),
            other_positions=other_positions,
            contact=f("ch"),
            power=f("ph"),
            gb_tendency=f("gf"),
            pull_tendency=f("pl"),
            vs_left=f("vl"),
            fielding=f("fa"),
            arm=f("arm"),
            speed=f("sp"),
            durability=f("durability", 50.0),
        )


@dataclass
class PitcherRatings:
    player_id: str
    bats: str
    velocity: float  # derived from arm
    control: float
    movement: float
    gb_tendency: float
    vs_left: float
    hold_runner: float
    endurance: float
    durability: float
    fielding: float
    arm: float
    repertoire: Dict[str, float]

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "PitcherRatings":
        def f(key: str, default: float = 50.0) -> float:
            try:
                return float(row.get(key, default))
            except (TypeError, ValueError):
                return default

        repertoire = {k: f(k) for k in PITCH_KEYS if f(k, 0.0) > 0.0}
        return cls(
            player_id=str(row.get("player_id", "")),
            bats=str(row.get("bats", "") or "R").upper(),
            velocity=f("arm"),
            control=f("control"),
            movement=f("movement"),
            gb_tendency=f("gf"),
            vs_left=f("vl"),
            hold_runner=f("hold_runner", 50.0),
            endurance=f("endurance"),
            durability=f("durability", 50.0),
            fielding=f("fa"),
            arm=f("arm"),
            repertoire=repertoire,
        )


@dataclass
class FieldingAlignment:
    positions: Dict[str, str]  # player_id -> position code (e.g., "SS", "CF")


@dataclass
class TeamState:
    lineup: List[str]
    pitchers: List[str]
    defense: FieldingAlignment
