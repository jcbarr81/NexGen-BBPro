from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import math

from .models import BatterRatings
from .config import TuningConfig


INFIELD_POS = {"1B", "2B", "3B", "SS", "C", "P"}
OUTFIELD_POS = {"LF", "CF", "RF"}


@dataclass
class DefenseRatings:
    infield: float
    outfield: float
    arm: float


def build_default_defense(batters: List[BatterRatings]) -> Dict[str, BatterRatings]:
    """Assign fielders to positions based on primary/other positions."""

    positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
    remaining = batters[:]
    defense: Dict[str, BatterRatings] = {}

    def select_for_pos(pos: str) -> BatterRatings | None:
        candidates = [
            b
            for b in remaining
            if b.primary_position == pos or pos in b.other_positions
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda b: b.fielding)
        return best

    for pos in positions:
        choice = select_for_pos(pos)
        if choice is None and remaining:
            choice = max(remaining, key=lambda b: b.fielding)
        if choice:
            defense[pos] = choice
            remaining.remove(choice)
    return defense


def compute_defense_ratings(defense: Dict[str, BatterRatings], tuning: TuningConfig) -> DefenseRatings:
    def_score_in = []
    def_score_out = []
    arms = []
    for pos, player in defense.items():
        rating = player.fielding
        arm = player.arm
        arms.append(arm)
        if pos in OUTFIELD_POS:
            def_score_out.append(rating)
        else:
            def_score_in.append(rating)
    infield = sum(def_score_in) / len(def_score_in) if def_score_in else 50.0
    outfield = sum(def_score_out) / len(def_score_out) if def_score_out else 50.0
    arm_avg = sum(arms) / len(arms) if arms else 50.0

    infield *= tuning.get("range_scale", 1.0)
    outfield *= tuning.get("range_scale", 1.0)
    arm_avg *= tuning.get("arm_strength_scale", 1.0)
    return DefenseRatings(infield=infield, outfield=outfield, arm=arm_avg)


def out_probability(
    *,
    ball_type: str,
    exit_velo: float,
    launch_angle: float,
    defense: DefenseRatings,
    tuning: TuningConfig,
) -> float:
    if ball_type == "gb":
        base = 0.72
        def_adj = (defense.infield - 50.0) / 250.0
    elif ball_type == "ld":
        base = 0.25
        def_adj = (defense.outfield - 50.0) / 300.0
    else:
        base = 0.68
        def_adj = (defense.outfield - 50.0) / 230.0

    quality_adj = (exit_velo - 90.0) / 300.0
    out_prob = base + def_adj - quality_adj
    return max(0.02, min(0.98, out_prob))


def double_play_probability(
    *,
    runner_speed: float,
    defense: DefenseRatings,
    tuning: TuningConfig,
) -> float:
    base = 0.14
    def_adj = (defense.infield - 50.0) / 250.0
    speed_adj = (runner_speed - 50.0) / 220.0
    prob = base + def_adj - speed_adj
    return max(0.03, min(0.45, prob))
