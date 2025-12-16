from __future__ import annotations

import inspect
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from models.player import Player
from models.pitcher import Pitcher
from .playbalance_config import PlayBalanceConfig
from .physics import Physics
from .batter_ai import BatterAI, record_auto_take
from .pitcher_ai import PitcherAI


@dataclass
class PitchContext:
    """Immutable inputs for resolving a single pitch."""

    balls: int
    strikes: int
    pitcher: Pitcher
    batter: Player
    objective: str
    control_roll: float
    target_dx: float
    target_dy: float
    pitch_type: str
    pitch_speed: float
    distance: float
    x_off: float
    y_off: float
    in_zone: bool


@dataclass
class PitchOutcome:
    """Result of resolving swing/take against a pitch."""

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
    contact_quality: float
    decision_breakdown: Dict[str, Any] | None
    decision_random: float
    auto_take: bool = False
    auto_take_reason: str | None = None
    auto_take_threshold: float | None = None
    auto_take_distance: float | None = None


def resolve_pitch(
    cfg: PlayBalanceConfig,
    physics: Physics,
    batter_ai: BatterAI,
    pitcher_ai: PitcherAI,
    *,
    batter: Player,
    pitcher: Pitcher,
    balls: int,
    strikes: int,
    control_roll: float,
    target_dx: float,
    target_dy: float,
    pitch_type: str | None = None,
    objective: str | None = None,
    rng: random.Random | None = None,
) -> Tuple[PitchContext, PitchOutcome]:
    """Resolve swing/take decision and contact against a single pitch.

    Returns a :class:`PitchContext` snapshot and a :class:`PitchOutcome`.
    """

    rng = rng or random
    selected_pitch_type = pitch_type
    selected_objective = objective
    if selected_pitch_type is None or selected_objective is None:
        chosen_pitch, chosen_obj = pitcher_ai.select_pitch(
            pitcher, balls=balls, strikes=strikes
        )
        if selected_pitch_type is None:
            selected_pitch_type = chosen_pitch
        if selected_objective is None:
            selected_objective = chosen_obj
    pitch_type = selected_pitch_type
    objective = selected_objective
    pitch_speed = physics.pitch_velocity(pitch_type, pitcher.arm, rand=control_roll)
    width, height = physics.control_box(pitch_type)

    frac = control_roll
    control_pct = min(1.0, max(0.0, pitcher.control / 100.0))
    miss_scale = float(cfg.get("pitchMissScale", 100.0))
    if miss_scale <= 0:
        miss_scale = 100.0
    miss_diff = frac - (frac * control_pct)
    miss_pct = miss_diff * 100.0 if miss_diff > 0 else 0.0
    miss_amt = miss_diff * miss_scale if miss_diff > 0 else 0.0
    max_miss_cfg = cfg.get("maxPitchMiss", None)
    max_miss = float(max_miss_cfg) if max_miss_cfg not in (None, 0, "0") else None
    if miss_amt > 0 and max_miss is not None and max_miss > 0:
        miss_amt = min(miss_amt, max_miss)
    if miss_amt > 0:
        width, height = physics.expand_control_box(width, height, miss_amt)
    base_expand = float(cfg.get("controlMissBaseExpansion", 1.5))
    if base_expand > 0 and control_pct < 0.6:
        expand_amt = base_expand * (1.0 - control_pct)
        width += expand_amt
        height += expand_amt

    x_off = target_dx + (frac * 2 - 1) * width
    y_off = target_dy + (frac * 2 - 1) * height
    exp_dx, exp_dy = physics.pitch_break(pitch_type, rand=0.5)
    x_off -= exp_dx
    y_off -= exp_dy
    dx, dy = physics.pitch_break(pitch_type, rand=frac)
    x_off += dx
    y_off += dy
    dist_raw = max(abs(x_off), abs(y_off))
    base_dist = int(round(max(width, height) * 0.8))
    break_dist = int(round(dist_raw * 0.8))
    dist = max(base_dist, break_dist)
    if miss_amt <= 0:
        inc_pct = float(cfg.get("controlBoxIncreaseEffCOPct", 0.0))
        if inc_pct > 0 and frac > 0:
            miss_amt_pct = miss_pct
            if miss_amt_pct > 0:
                inc = miss_amt_pct * inc_pct / 100.0
                dist = max(dist, int(round(max(width + inc, height + inc) * 0.8)))
    penalty = float(cfg.get("controlMissPenaltyDist", 5.0))
    if penalty > 0 and control_pct < 0.6:
        dist += int(math.ceil((1.0 - control_pct) * penalty))
    plate_w = getattr(cfg, "plateWidth", 3)
    plate_h = getattr(cfg, "plateHeight", 3)
    in_zone = dist <= max(plate_w, plate_h)

    dec_r = rng.random()
    if miss_pct > 0:
        pitch_speed = physics.reduce_pitch_velocity_for_miss(
            pitch_speed, miss_pct, rand=dec_r
        )

    decide_fn = batter_ai.decide_swing
    swing_kwargs = {
        "pitch_type": pitch_type,
        "balls": balls,
        "strikes": strikes,
        "dist": dist,
        "objective": objective,
        "random_value": dec_r,
    }
    params = inspect.signature(decide_fn).parameters
    allows_variadic = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    if allows_variadic or "dx" in params:
        swing_kwargs["dx"] = x_off
    if allows_variadic or "dy" in params:
        swing_kwargs["dy"] = y_off
    swing, contact_quality = decide_fn(
        batter,
        pitcher,
        **swing_kwargs,
    )
    breakdown = getattr(batter_ai, "last_swing_breakdown", None)
    contact = getattr(batter_ai, "last_contact", contact_quality > 0)

    outcome = PitchOutcome(
        swing=bool(swing),
        contact=bool(contact),
        foul=False,
        ball_in_play=False,
        hit=False,
        ball=not in_zone and not swing,
        called_strike=in_zone and not swing,
        walk=False,
        strikeout=False,
        hbp=False,
        contact_quality=contact_quality,
        decision_breakdown=breakdown,
        decision_random=dec_r,
        auto_take=False,
        auto_take_reason=None,
        auto_take_threshold=None,
        auto_take_distance=None,
    )

    # Auto-take enforcement for obvious balls and late-count protection.
    if not outcome.swing and not in_zone:
        base_take = float(cfg.get("autoTakeDistanceBase", 3.0))
        step_take = float(cfg.get("autoTakeDistanceBallStep", 0.5))
        min_take = float(cfg.get("autoTakeDistanceMin", 1.5))
        auto_take_threshold = max(min_take, base_take - balls * step_take)
        buffer = float(cfg.get("autoTakeDistanceBuffer", 0.0))
        force_take = (dist - auto_take_threshold) >= buffer
        force_reason = "distance" if force_take else None
        if not force_take and balls >= 3:
            force_three_ball = bool(int(getattr(cfg, "autoTakeForceThreeBall", 1)))
            force_full_count = bool(
                int(
                    getattr(
                        cfg,
                        "autoTakeForceFullCount",
                        getattr(cfg, "autoTakeForceThreeBall", 1),
                    )
                )
            )
            if strikes >= 2:
                force_take = force_full_count
                if force_take:
                    force_reason = "full"
            else:
                force_take = force_three_ball
                if force_take:
                    force_reason = "three_ball"
        if force_take:
            chase_key = f"autoTakeChaseChance{balls}{strikes}"
            chase_override = getattr(cfg, "values", {}).get(chase_key, None)
            chase_base: float | None
            if chase_override not in (None, ""):
                try:
                    chase_base = float(chase_override)
                except (TypeError, ValueError):
                    chase_base = None
            else:
                chase_base = None
            if chase_base is None:
                chase_base = float(getattr(cfg, "autoTakeDefaultChaseChance", 0.0) or 0.0)
                if balls >= 3:
                    three_ball_chance = float(
                        getattr(cfg, "autoTakeThreeBallChaseChance", 0.0) or 0.0
                    )
                    chase_base = max(chase_base, three_ball_chance)
            if chase_base > 0.0 and rng.random() < chase_base:
                force_take = False
                force_reason = None
        if force_take:
            outcome.contact = False
            outcome.contact_quality = 0.0
            outcome.auto_take = True
            outcome.auto_take_reason = force_reason or "other"
            outcome.auto_take_threshold = float(auto_take_threshold)
            outcome.auto_take_distance = float(dist)
            record_auto_take(
                cfg,
                balls=balls,
                strikes=strikes,
                reason=outcome.auto_take_reason,
                distance=float(dist),
                threshold=float(auto_take_threshold),
            )

    context = PitchContext(
        balls=balls,
        strikes=strikes,
        pitcher=pitcher,
        batter=batter,
        objective=objective,
        control_roll=control_roll,
        target_dx=target_dx,
        target_dy=target_dy,
        pitch_type=pitch_type,
        pitch_speed=pitch_speed,
        distance=dist,
        x_off=x_off,
        y_off=y_off,
        in_zone=in_zone,
    )
    return context, outcome
