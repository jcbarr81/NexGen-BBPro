from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import math
import random

from .config import TuningConfig
from .park import Park


@dataclass
class PitchResult:
    pitch_type: str
    pitch_quality: float
    velocity: float
    location: tuple[float, float]
    in_zone: bool
    swing: bool
    contact: bool
    foul: bool
    in_play: bool
    outcome: str
    exit_velo: float | None = None
    launch_angle: float | None = None
    spray_angle: float | None = None
    distance: float | None = None
    ball_type: str | None = None
    hit_type: str | None = None


def sample_pitch_location(command: float, tuning: TuningConfig) -> tuple[float, float]:
    spread = max(0.1, (100 - command) / 300.0)
    return (random.gauss(0, spread), random.gauss(0, spread))


def sample_pitch_velocity(base_velo: float, fatigue: float, tuning: TuningConfig) -> float:
    scale = tuning.get("velocity_scale", 1.0)
    return base_velo * scale * fatigue


def simulate_pitch(
    *,
    batter: Dict[str, float],
    pitcher: Dict[str, Any],
    tuning: TuningConfig,
    count: tuple[int, int],
) -> PitchResult:
    """Placeholder pitch simulation; will be replaced with full physics model."""

    pitch_type = max(pitcher.get("repertoire", {"fb": 50}), key=pitcher["repertoire"].get)
    pitch_quality = float(pitcher.get("repertoire", {}).get(pitch_type, 50.0))
    fatigue = pitcher.get("fatigue_factor", 1.0)
    velocity = sample_pitch_velocity(pitcher.get("velocity", 90.0), fatigue, tuning)
    loc = sample_pitch_location(pitcher.get("control", 50.0), tuning)

    # Simple swing decision: zone vs chase.
    balls, strikes = count
    zone_scale = tuning.get("zone_swing_scale", 1.0)
    chase_scale = tuning.get("chase_scale", 1.0)
    eye = batter.get("eye", batter.get("contact", 50.0))
    in_zone = abs(loc[0]) < 0.5 and abs(loc[1]) < 0.5
    zone_base = 0.48 + (eye - 50.0) / 250.0
    chase_base = 0.22 - (eye - 50.0) / 320.0
    base_swing = (zone_base * zone_scale) if in_zone else (chase_base * chase_scale)
    if strikes >= 2:
        base_swing += 0.10 * tuning.get("two_strike_aggression_scale", 1.0)
    walk_scale = tuning.get("walk_scale", 1.0)
    if walk_scale > 0:
        base_swing /= walk_scale
    swing = random.random() < base_swing

    contact = False
    foul = False
    in_play = False
    outcome = "strike" if in_zone else "ball"
    exit_velo = None
    launch_angle = None
    spray_angle = None
    distance = None
    ball_type = None
    hit_type = None

    if swing:
        pitch_quality = (
            pitcher.get("control", 50.0) * 0.4
            + pitcher.get("movement", 50.0) * 0.4
            + pitch_quality * 0.2
        )
        pitch_quality *= tuning.get("pitching_dom_scale", 1.0)
        contact_base = batter.get("contact", 50.0) - (pitch_quality - 50.0) * 0.4
        contact_prob = min(
            0.95,
            max(0.05, (contact_base / 100.0) * tuning.get("contact_quality_scale", 1.0)),
        )
        contact_prob /= max(0.1, tuning.get("k_scale", 1.0))
        contact = random.random() < contact_prob
        if contact:
            # Rough EV/LA model
            exit_velo = max(
                50.0,
                (velocity * 0.42) + (batter.get("power", 50.0) * 0.45),
            )
            exit_velo *= tuning.get("offense_scale", 1.0)
            gb_bias = (batter.get("gb_tendency", 50.0) - 50.0) / 10.0
            launch_angle = random.gauss(12.0 - gb_bias, 16.0)
            launch_angle *= tuning.get("gb_fb_tilt", 1.0)
            pull_bias = (batter.get("pull_tendency", 50.0) - 50.0) / 2.0
            spray_angle = random.gauss(pull_bias, 18.0)
            foul = random.random() < 0.18
            in_play = not foul
            outcome = "in_play" if in_play else "foul"
        else:
            outcome = "swinging_strike"

    return PitchResult(
        pitch_type=pitch_type,
        pitch_quality=pitch_quality,
        velocity=velocity,
        location=loc,
        in_zone=in_zone,
        swing=swing,
        contact=contact,
        foul=foul,
        in_play=in_play,
        outcome=outcome,
        exit_velo=exit_velo,
        launch_angle=launch_angle,
        spray_angle=spray_angle,
        distance=distance,
        ball_type=ball_type,
        hit_type=hit_type,
    )


def classify_ball_type(launch_angle: float) -> str:
    if launch_angle < 10.0:
        return "gb"
    if launch_angle < 25.0:
        return "ld"
    return "fb"


def spray_to_field_angle(spray_deg: float) -> float:
    """Convert spray angle to stadium angle in radians (0=RF line, pi/2=LF line)."""

    return max(0.0, min(math.pi / 2, math.radians(45.0 - spray_deg)))


def estimate_carry_distance(
    exit_velo: float,
    launch_angle: float,
    tuning: TuningConfig,
    park: Park,
) -> float:
    ev_ft_s = exit_velo * 1.467
    theta = math.radians(max(1.0, min(60.0, launch_angle)))
    g = 32.17
    carry_scale = 0.75 * tuning.get("hr_scale", 1.0) * tuning.get("offense_scale", 1.0)
    carry_scale *= tuning.get("altitude_scale", 1.0) * park.park_factor
    return (ev_ft_s**2 / g) * math.sin(2 * theta) * carry_scale


def resolve_batted_ball(
    *,
    exit_velo: float,
    launch_angle: float,
    spray_angle: float,
    park: Park,
    tuning: TuningConfig,
) -> tuple[float, bool, str, str | None]:
    """Return (distance, is_hr, ball_type, hit_type)."""

    ball_type = classify_ball_type(launch_angle)
    dist = estimate_carry_distance(exit_velo, launch_angle, tuning, park)
    angle = spray_to_field_angle(spray_angle)
    wall = park.stadium.wall_distance(angle) * tuning.get("park_size_scale", 1.0)
    if dist > wall:
        return dist, True, ball_type, "hr"
    # Non-HR hit type determined by wall-relative distance.
    if dist >= park.stadium.triple_distance(angle):
        hit_type = "triple"
    elif dist >= park.stadium.double_distance(angle):
        hit_type = "double"
    else:
        hit_type = "single"
    return dist, False, ball_type, hit_type
