"""Shared archetype sampling helpers for hitters and pitchers."""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, Iterable, Mapping


@dataclass(frozen=True)
class RatingRange:
    low: int
    high: int
    jitter: int = 3


def _sample_range(band: RatingRange) -> int:
    value = random.uniform(band.low, band.high)
    if band.jitter:
        value += random.uniform(-band.jitter, band.jitter)
    return int(max(30, min(99, round(value))))


@dataclass(frozen=True)
class HitterArchetype:
    name: str
    weight: float
    contact: RatingRange
    power: RatingRange
    speed: RatingRange
    discipline: RatingRange


HITTER_ARCHETYPES: Dict[str, HitterArchetype] = {
    "contact": HitterArchetype(
        name="contact",
        weight=0.35,
        contact=RatingRange(68, 88, jitter=4),
        power=RatingRange(40, 62, jitter=4),
        speed=RatingRange(58, 80, jitter=4),
        discipline=RatingRange(62, 85, jitter=5),
    ),
    "power": HitterArchetype(
        name="power",
        weight=0.20,
        contact=RatingRange(48, 66, jitter=4),
        power=RatingRange(70, 95, jitter=5),
        speed=RatingRange(40, 70, jitter=5),
        discipline=RatingRange(45, 65, jitter=4),
    ),
    "balanced": HitterArchetype(
        name="balanced",
        weight=0.35,
        contact=RatingRange(58, 78, jitter=5),
        power=RatingRange(58, 78, jitter=5),
        speed=RatingRange(50, 75, jitter=4),
        discipline=RatingRange(52, 70, jitter=4),
    ),
    "speed_disc": HitterArchetype(
        name="speed_disc",
        weight=0.10,
        contact=RatingRange(60, 78, jitter=4),
        power=RatingRange(48, 68, jitter=4),
        speed=RatingRange(72, 92, jitter=4),
        discipline=RatingRange(68, 88, jitter=5),
    ),
}


def choose_hitter_archetype(name: str | None = None) -> HitterArchetype:
    if name and name in HITTER_ARCHETYPES:
        return HITTER_ARCHETYPES[name]
    weights = [arch.weight for arch in HITTER_ARCHETYPES.values()]
    choices = list(HITTER_ARCHETYPES.values())
    return random.choices(choices, weights=weights)[0]


def sample_hitter_ratings(name: str | None = None) -> Dict[str, int]:
    archetype = choose_hitter_archetype(name)
    return {
        "contact": _sample_range(archetype.contact),
        "power": _sample_range(archetype.power),
        "speed": _sample_range(archetype.speed),
        "discipline": _sample_range(archetype.discipline),
        "archetype": archetype.name,
    }


def infer_hitter_archetype(row: Mapping[str, str | int]) -> str:
    contact = float(row.get("ch", 0) or 0)
    power = float(row.get("ph", 0) or 0)
    speed = float(row.get("sp", 0) or 0)
    discipline = float(row.get("vl", 0) or 0)
    if speed >= 75 and discipline >= 70:
        return "speed_disc"
    if contact >= power + 8:
        return "contact"
    if power >= contact + 8:
        return "power"
    return "balanced"


@dataclass(frozen=True)
class PitcherArchetype:
    name: str
    role: str  # SP, RP
    preferred_role: str = ""
    weight: float = 1.0
    velocity: RatingRange = RatingRange(60, 85)
    control: RatingRange = RatingRange(55, 80)
    movement: RatingRange = RatingRange(55, 82)
    endurance: RatingRange = RatingRange(50, 80)
    hold_runner: RatingRange = RatingRange(50, 75)


STARTER_ARCHETYPES: Dict[str, PitcherArchetype] = {
    "power_starter": PitcherArchetype(
        name="power_starter",
        role="SP",
        weight=0.30,
        velocity=RatingRange(72, 95, jitter=5),
        control=RatingRange(55, 70, jitter=4),
        movement=RatingRange(60, 80, jitter=4),
        endurance=RatingRange(72, 92, jitter=4),
        hold_runner=RatingRange(48, 70, jitter=4),
    ),
    "finesse_starter": PitcherArchetype(
        name="finesse_starter",
        role="SP",
        weight=0.25,
        velocity=RatingRange(58, 74, jitter=4),
        control=RatingRange(70, 88, jitter=4),
        movement=RatingRange(70, 88, jitter=4),
        endurance=RatingRange(68, 88, jitter=4),
        hold_runner=RatingRange(60, 80, jitter=4),
    ),
    "balanced_starter": PitcherArchetype(
        name="balanced_starter",
        role="SP",
        weight=0.35,
        velocity=RatingRange(65, 82, jitter=4),
        control=RatingRange(60, 78, jitter=4),
        movement=RatingRange(65, 82, jitter=4),
        endurance=RatingRange(65, 85, jitter=4),
        hold_runner=RatingRange(55, 75, jitter=4),
    ),
    "specialist_starter": PitcherArchetype(
        name="specialist_starter",
        role="SP",
        weight=0.10,
        velocity=RatingRange(55, 70, jitter=4),
        control=RatingRange(60, 75, jitter=4),
        movement=RatingRange(75, 90, jitter=4),
        endurance=RatingRange(60, 80, jitter=4),
        hold_runner=RatingRange(55, 75, jitter=4),
    ),
}


RELIEF_ARCHETYPES: Dict[str, PitcherArchetype] = {
    "closer": PitcherArchetype(
        name="closer",
        role="RP",
        preferred_role="CL",
        weight=0.10,
        velocity=RatingRange(85, 99, jitter=4),
        control=RatingRange(60, 75, jitter=3),
        movement=RatingRange(65, 85, jitter=4),
        endurance=RatingRange(32, 48, jitter=3),
        hold_runner=RatingRange(55, 75, jitter=4),
    ),
    "setup": PitcherArchetype(
        name="setup",
        role="RP",
        preferred_role="SU",
        weight=0.15,
        velocity=RatingRange(75, 95, jitter=4),
        control=RatingRange(60, 78, jitter=4),
        movement=RatingRange(60, 80, jitter=4),
        endurance=RatingRange(40, 58, jitter=4),
        hold_runner=RatingRange(55, 75, jitter=4),
    ),
    "middle_relief": PitcherArchetype(
        name="middle_relief",
        role="RP",
        weight=0.50,
        velocity=RatingRange(65, 85, jitter=4),
        control=RatingRange(55, 72, jitter=4),
        movement=RatingRange(55, 75, jitter=4),
        endurance=RatingRange(45, 65, jitter=4),
        hold_runner=RatingRange(50, 72, jitter=4),
    ),
    "long_relief": PitcherArchetype(
        name="long_relief",
        role="RP",
        preferred_role="LR",
        weight=0.25,
        velocity=RatingRange(62, 78, jitter=4),
        control=RatingRange(58, 75, jitter=4),
        movement=RatingRange(60, 78, jitter=4),
        endurance=RatingRange(55, 72, jitter=4),
        hold_runner=RatingRange(52, 72, jitter=4),
    ),
}


def _weighted_choice(items: Iterable[PitcherArchetype]) -> PitcherArchetype:
    entries = list(items)
    weights = [entry.weight for entry in entries]
    return random.choices(entries, weights=weights)[0]


def choose_pitcher_archetype(
    name: str | None = None,
    role_hint: str | None = None,
) -> PitcherArchetype:
    if name:
        return (
            STARTER_ARCHETYPES.get(name)
            or RELIEF_ARCHETYPES.get(name)
            or RELIEF_ARCHETYPES.get("middle_relief")
        )
    if role_hint == "SP":
        return _weighted_choice(STARTER_ARCHETYPES.values())
    if role_hint == "RP":
        return _weighted_choice(RELIEF_ARCHETYPES.values())
    # Decide starter vs reliever split (approx MLB 5 SP per 8-9 pitchers ≈ 55-60%)
    if random.random() < 0.6:
        return _weighted_choice(STARTER_ARCHETYPES.values())
    return _weighted_choice(RELIEF_ARCHETYPES.values())


def sample_pitcher_core(name: str | None = None, role_hint: str | None = None) -> Dict[str, int | str]:
    archetype = choose_pitcher_archetype(name, role_hint=role_hint)
    return {
        "archetype": archetype.name,
        "role": archetype.role,
        "preferred_role": archetype.preferred_role,
        "velocity": _sample_range(archetype.velocity),
        "control": _sample_range(archetype.control),
        "movement": _sample_range(archetype.movement),
        "endurance": _sample_range(archetype.endurance),
        "hold_runner": _sample_range(archetype.hold_runner),
    }


def infer_pitcher_archetype(row: Mapping[str, str | int]) -> str:
    preferred = (row.get("preferred_pitching_role") or "").upper()
    role = (row.get("role") or "").upper()
    if preferred == "CL":
        return "closer"
    if preferred == "SU":
        return "setup"
    if preferred == "LR":
        return "long_relief"
    if role == "SP":
        control = float(row.get("control", 0) or 0)
        velocity = float(row.get("fb", row.get("arm", 0)) or 0)
        movement = float(row.get("movement", 0) or 0)
        if velocity >= control + 8:
            return "power_starter"
        if control >= velocity + 8:
            return "finesse_starter"
        if movement >= velocity + 6:
            return "specialist_starter"
        return "balanced_starter"
    # default to bullpen buckets
    velocity = float(row.get("fb", row.get("arm", 0)) or 0)
    if velocity >= 85:
        return "setup"
    return "middle_relief"
