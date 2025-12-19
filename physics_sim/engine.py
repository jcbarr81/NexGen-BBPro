from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List
import random

from .config import load_tuning, TuningConfig
from .models import BatterRatings, PitcherRatings
from .fielding import (
    build_default_defense,
    compute_defense_ratings,
    out_probability,
    double_play_probability,
)
from .park import load_park, Park
from .physics import simulate_pitch, resolve_batted_ball, PitchResult


@dataclass
class GameResult:
    totals: Dict[str, int]
    pitch_log: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseState:
    first: BatterRatings | None = None
    second: BatterRatings | None = None
    third: BatterRatings | None = None


@dataclass
class PitcherState:
    pitcher: PitcherRatings
    pitches: int = 0
    fatigue_start: float = 0.0
    fatigue_limit: float = 0.0
    last_penalty: float = 0.0


def _pitcher_usage_limits(pitcher: PitcherRatings) -> tuple[float, float]:
    endurance = pitcher.endurance if pitcher.endurance > 0 else 50.0
    fatigue_start = 35.0 + (endurance * 0.9)
    fatigue_limit = fatigue_start + 15.0 + (endurance * 0.3)
    return fatigue_start, fatigue_limit


def _fatigue_penalty(state: PitcherState, tuning: TuningConfig) -> float:
    if state.pitches <= state.fatigue_start:
        return 0.0
    span = max(1.0, state.fatigue_limit - state.fatigue_start)
    raw = (state.pitches - state.fatigue_start) / span
    raw *= tuning.get("fatigue_decay_scale", 1.0)
    durability = state.pitcher.durability if state.pitcher.durability > 0 else 50.0
    raw *= 1.0 + (50.0 - durability) / 200.0
    return min(1.5, max(0.0, raw))


def _fatigue_factors(penalty: float) -> tuple[float, float, float]:
    velocity_factor = max(0.85, 1.0 - (0.15 * penalty))
    command_factor = max(0.60, 1.0 - (0.30 * penalty))
    movement_factor = max(0.65, 1.0 - (0.25 * penalty))
    return velocity_factor, command_factor, movement_factor


def _pitcher_usage_summary(state: PitcherState) -> Dict[str, float | str]:
    return {
        "player_id": state.pitcher.player_id,
        "pitches": state.pitches,
        "fatigue_start": round(state.fatigue_start, 1),
        "fatigue_limit": round(state.fatigue_limit, 1),
        "fatigue_penalty": round(state.last_penalty, 3),
    }


def _advance_on_walk(bases: BaseState, batter: BatterRatings) -> int:
    runs = 0
    if bases.first and bases.second and bases.third:
        runs += 1
        bases.third = bases.second
        bases.second = bases.first
        bases.first = batter
        return runs
    if bases.second and bases.first and not bases.third:
        bases.third = bases.second
        bases.second = bases.first
        bases.first = batter
        return runs
    if bases.first and not bases.second:
        bases.second = bases.first
        bases.first = batter
        return runs
    bases.first = batter
    return runs


def _advance_prob(speed: float, arm: float, tuning: TuningConfig, extra: float = 0.0) -> float:
    base = 0.45 + (speed - 50.0) / 200.0 - (arm - 50.0) / 250.0 + extra
    base *= tuning.get("advancement_aggression_scale", 1.0)
    return max(0.05, min(0.95, base))


def _advance_on_hit(
    *,
    bases: BaseState,
    batter: BatterRatings,
    hit_type: str,
    defense_arm: float,
    tuning: TuningConfig,
) -> int:
    runs = 0
    if hit_type == "hr":
        runs += 1
        for runner in (bases.first, bases.second, bases.third):
            if runner is not None:
                runs += 1
        bases.first = bases.second = bases.third = None
        return runs

    if hit_type == "triple":
        for runner in (bases.first, bases.second, bases.third):
            if runner is not None:
                runs += 1
        bases.first = bases.second = None
        bases.third = batter
        return runs

    if hit_type == "double":
        if bases.third:
            runs += 1
        if bases.second:
            runs += 1
        if bases.first:
            prob = _advance_prob(bases.first.speed, defense_arm, tuning, extra=0.10)
            if random.random() < prob:
                runs += 1
            else:
                bases.third = bases.first
        bases.first = None
        bases.second = batter
        bases.third = bases.third if bases.third else None
        return runs

    # Single
    if bases.third:
        runs += 1
    if bases.second:
        prob = _advance_prob(bases.second.speed, defense_arm, tuning, extra=0.10)
        if random.random() < prob:
            runs += 1
        else:
            bases.third = bases.second
    if bases.first:
        prob = _advance_prob(bases.first.speed, defense_arm, tuning, extra=0.0)
        if random.random() < prob:
            bases.third = bases.first
        else:
            bases.second = bases.first
    bases.first = batter
    return runs


def _batter_context(batter: BatterRatings, pitcher: PitcherRatings) -> Dict[str, float]:
    eye = batter.contact * 0.8 + (100.0 - pitcher.control) * 0.2
    return {
        "contact": batter.contact,
        "power": batter.power,
        "gb_tendency": batter.gb_tendency,
        "pull_tendency": batter.pull_tendency,
        "eye": eye,
    }


def simulate_game(
    *,
    batters: List[BatterRatings],
    pitchers: List[PitcherRatings],
    park_name: str | None = None,
    seed: int | None = None,
    tuning_overrides: Dict[str, Any] | None = None,
) -> GameResult:
    """Very early stub of the physics-based game simulation.

    This will be expanded to handle full rosters, substitutions, defense, and
    realistic fatigue/usage. For now it runs a minimal pitch loop for a single
    matchup to prove out the scaffolding.
    """

    rng = random.Random(seed)
    random.seed(seed)
    tuning: TuningConfig = load_tuning(overrides=tuning_overrides)
    park: Park = load_park(park_name)

    totals = {
        "pa": 0,
        "ab": 0,
        "h": 0,
        "bb": 0,
        "k": 0,
        "hr": 0,
        "r": 0,
        "pitches": 0,
    }
    pitch_log: List[Dict[str, Any]] = []

    # Basic lineup/defense selection for a two-team matchup.
    if len(batters) >= 18:
        away_lineup = batters[:9]
        home_lineup = batters[9:18]
    else:
        away_lineup = batters[:9] if len(batters) >= 9 else batters
        home_lineup = list(away_lineup)
    away_defense = build_default_defense(away_lineup)
    home_defense = build_default_defense(home_lineup)
    away_defense_ratings = compute_defense_ratings(away_defense, tuning)
    home_defense_ratings = compute_defense_ratings(home_defense, tuning)

    away_pitcher = pitchers[0]
    home_pitcher = pitchers[1] if len(pitchers) > 1 else pitchers[0]
    away_state = PitcherState(away_pitcher)
    home_state = PitcherState(home_pitcher)
    away_state.fatigue_start, away_state.fatigue_limit = _pitcher_usage_limits(
        away_pitcher
    )
    home_state.fatigue_start, home_state.fatigue_limit = _pitcher_usage_limits(
        home_pitcher
    )
    away_index = 0
    home_index = 0

    def play_half_inning(
        lineup: List[BatterRatings],
        pitcher_state: PitcherState,
        defense_ratings,
        batter_index: int,
    ) -> tuple[int, int]:
        outs = 0
        bases = BaseState()
        while outs < 3:
            balls = strikes = 0
            batter = lineup[batter_index % len(lineup)]
            batter_index += 1
            totals["pa"] += 1
            while True:
                pitcher_state.pitches += 1
                penalty = _fatigue_penalty(pitcher_state, tuning)
                pitcher_state.last_penalty = penalty
                velocity_factor, command_factor, movement_factor = _fatigue_factors(
                    penalty
                )
                pitcher = pitcher_state.pitcher
                res: PitchResult = simulate_pitch(
                    batter=_batter_context(batter, pitcher),
                    pitcher={
                        "repertoire": pitcher.repertoire or {"fb": 50},
                        "velocity": 80.0 + (pitcher.arm * 0.2),
                        "control": pitcher.control * command_factor,
                        "movement": pitcher.movement * movement_factor,
                        "fatigue_factor": velocity_factor,
                    },
                    tuning=tuning,
                    count=(balls, strikes),
                )
                totals["pitches"] += 1
                entry = res.__dict__.copy()
                entry["pitch_count"] = pitcher_state.pitches
                entry["fatigue_penalty"] = penalty
                pitch_log.append(entry)

                if res.outcome == "ball":
                    balls += 1
                    if balls >= 4:
                        totals["bb"] += 1
                        totals["r"] += _advance_on_walk(bases, batter)
                        break
                elif res.outcome == "strike":
                    strikes += 1
                    if strikes >= 3:
                        totals["k"] += 1
                        outs += 1
                        break
                elif res.outcome == "swinging_strike":
                    strikes += 1
                    if strikes >= 3:
                        totals["k"] += 1
                        outs += 1
                        break
                elif res.outcome == "foul":
                    strikes = min(2, strikes + 1)
                elif res.outcome == "in_play":
                    totals["ab"] += 1
                    dist, is_hr, ball_type, hit_type = resolve_batted_ball(
                        exit_velo=res.exit_velo or 90.0,
                        launch_angle=res.launch_angle or 12.0,
                        spray_angle=res.spray_angle or 0.0,
                        park=park,
                        tuning=tuning,
                    )
                    res.distance = dist
                    res.ball_type = ball_type
                    res.hit_type = hit_type
                    pitch_log[-1].update(res.__dict__)
                    if is_hr:
                        totals["h"] += 1
                        totals["hr"] += 1
                        totals["r"] += _advance_on_hit(
                            bases=bases,
                            batter=batter,
                            hit_type="hr",
                            defense_arm=defense_ratings.arm,
                            tuning=tuning,
                        )
                        break

                    out_prob = out_probability(
                        ball_type=ball_type,
                        exit_velo=res.exit_velo or 90.0,
                        launch_angle=res.launch_angle or 12.0,
                        defense=defense_ratings,
                        tuning=tuning,
                    )
                    hit_prob = (1.0 - out_prob) * tuning.get("babip_scale", 1.0)
                    hit_prob = max(0.02, min(0.95, hit_prob))
                    if rng.random() < hit_prob:
                        totals["h"] += 1
                        totals["r"] += _advance_on_hit(
                            bases=bases,
                            batter=batter,
                            hit_type=hit_type or "single",
                            defense_arm=defense_ratings.arm,
                            tuning=tuning,
                        )
                    else:
                        if ball_type == "gb" and bases.first and outs < 2:
                            dp_prob = double_play_probability(
                                runner_speed=bases.first.speed,
                                defense=defense_ratings,
                                tuning=tuning,
                            )
                            if rng.random() < dp_prob:
                                outs += 2
                                bases.first = None
                                break
                        outs += 1
                    break
                if strikes >= 3:
                    totals["k"] += 1
                    outs += 1
                    break
                if balls >= 4:
                    totals["bb"] += 1
                    totals["r"] += _advance_on_walk(bases, batter)
                    break
        return outs, batter_index

    for _ in range(9):
        _, away_index = play_half_inning(
            away_lineup, home_state, home_defense_ratings, away_index
        )
        _, home_index = play_half_inning(
            home_lineup, away_state, away_defense_ratings, home_index
        )

    return GameResult(
        totals=totals,
        pitch_log=pitch_log,
        metadata={
            "park": park.name,
            "seed": seed,
            "pitcher_usage": {
                "away": _pitcher_usage_summary(away_state),
                "home": _pitcher_usage_summary(home_state),
            },
        },
    )
