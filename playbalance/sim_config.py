from __future__ import annotations

"""Helpers for loading and tuning :class:`PlayBalanceConfig`."""

import csv
import os
from typing import Tuple, Dict

from .playbalance_config import PlayBalanceConfig
from utils.path_utils import get_base_dir

# Scaling factor applied to outs on balls in play to tune the simulated
# batting average on balls in play (BABIP). Values below ``1`` decrease outs
# and raise BABIP, values above ``1`` increase outs and lower BABIP. ``1.0``
# uses the MLB averages without additional adjustment.
# Factor tuned so default ``babipScale`` of ``1.05`` yields MLB BABIP (~.291).
_BABIP_OUT_ADJUST = 1.142857


def apply_league_benchmarks(
    cfg: PlayBalanceConfig, benchmarks: Dict[str, float], babip_scale: float | None = None
) -> None:
    """Configure ``cfg`` using league-wide benchmark rates.

    Parameters
    ----------
    cfg:
        Configuration to update.
    benchmarks:
        Mapping of league averages.
    babip_scale:
        Optional scale applied to outs on balls in play. When ``None`` (the
        default) ``cfg.babip_scale`` is used.
    """

    # Base hit probability derived from league BABIP.  ``hitProbBase`` is
    # scaled down in :mod:`playbalance.simulation` so multiply the MLB BABIP
    # by ``1.5`` to produce a small additive term in the final hit probability
    # calculation.
    cfg.hitProbBase = benchmarks["babip"] * 1.50
    pip_pct = benchmarks["pitches_put_in_play_pct"]
    cfg.ballInPlayPitchPct = max(0, int(round(pip_pct * 100)) - 1)
    pitches_per_pa = benchmarks["pitches_per_pa"]
    if pitches_per_pa:
        cfg.swingProbScale = round(3.85 / pitches_per_pa, 2)
    else:
        cfg.swingProbScale = 1.0
    cfg.swingProbScale = max(0.9, min(cfg.swingProbScale, 1.15))

    z_swing_pct = benchmarks.get("z_swing_pct")
    o_swing_pct = benchmarks.get("o_swing_pct")
    if None not in (z_swing_pct, o_swing_pct):
        base_z = (cfg.swingProbSureStrike + cfg.swingProbCloseStrike) / 2
        base_o = (cfg.swingProbCloseBall + cfg.swingProbSureBall) / 2
        base_z *= cfg.swingProbScale
        base_o *= cfg.swingProbScale
        z_ratio = (z_swing_pct / base_z) if base_z else 1.0
        o_ratio = (o_swing_pct / base_o) if base_o else 1.0
        z_ratio *= getattr(cfg, "extra_z_swing_scale", 1.0) or 1.0
        o_ratio *= getattr(cfg, "extra_o_swing_scale", 1.0) or 1.0
        cfg.zSwingProbScale = round(max(0.9, min(z_ratio, 1.1)), 2)
        cfg.oSwingProbScale = round(max(0.6, min(o_ratio, 1.0)), 2)

    swing_pct = benchmarks.get("swing_pct")
    zone_pct = benchmarks.get("zone_pct")
    z_contact_pct = benchmarks.get("z_contact_pct")
    o_contact_pct = benchmarks.get("o_contact_pct")
    swstr_pct = benchmarks.get("swstr_pct")
    if None not in (
        swing_pct,
        zone_pct,
        z_swing_pct,
        o_swing_pct,
        z_contact_pct,
        o_contact_pct,
        swstr_pct,
    ):
        zone_swing = zone_pct * z_swing_pct
        o_swing = (1 - zone_pct) * o_swing_pct
        contact = zone_swing * z_contact_pct + o_swing * o_contact_pct
        foul_pct = max(contact - pip_pct, 0.0)
        called_strike_pct = zone_pct - zone_swing
        strike_pct = pip_pct + swstr_pct + foul_pct + called_strike_pct
        cfg.foulPitchBasePct = int(round(foul_pct * 100))
        cfg.leagueStrikePct = round(max(0.0, strike_pct * 100.0 - 4.0), 1)
        if strike_pct:
            cfg.foulStrikeBasePct = round((foul_pct / strike_pct) * 100, 1)

    # Derive outs on balls in play by type.  Start from MLB-average
    # probabilities and scale them so that the weighted mean matches the
    # league BABIP from the benchmark file.
    gb_pct = benchmarks.get("bip_gb_pct", 0.0)
    fb_pct = benchmarks.get("bip_fb_pct", 0.0)
    ld_pct = benchmarks.get("bip_ld_pct", 0.0)
    babip = benchmarks.get("babip", 0.0)
    base_gb, base_ld, base_fb = 0.76, 0.32, 0.86
    weighted_out = base_gb * gb_pct + base_fb * fb_pct + base_ld * ld_pct
    scale = ((1 - babip) / weighted_out) if weighted_out else 1.0
    applied_scale = cfg.babip_scale if babip_scale is None else babip_scale
    scale *= _BABIP_OUT_ADJUST * applied_scale
    if babip_scale is not None:
        cfg.babip_scale = babip_scale
    cfg.groundOutProb = round(min(max(base_gb * scale, 0.0), 1.0), 3)
    cfg.lineOutProb = round(min(max(base_ld * scale, 0.0), 1.0), 3)
    cfg.flyOutProb = round(min(max(base_fb * scale, 0.0), 1.0), 3)


def load_tuned_playbalance_config(
    babip_scale_param: float | None = None,
    baserunning_aggression: float | None = None,
    apply_benchmarks: bool = True,
) -> Tuple[PlayBalanceConfig, Dict[str, float]]:
    """Return a tuned :class:`PlayBalanceConfig` and MLB averages.

    Parameters
    ----------
    babip_scale_param:
        Optional scale applied to outs on balls in play. When ``None``
        (the default) the value is read from ``PlayBalanceConfig``.
    baserunning_aggression:
        Optional aggression factor for advancing on the basepaths. When
        ``None`` the value from ``PlayBalanceConfig`` is used.
    apply_benchmarks:
        When ``False`` the configuration is returned without applying league
        benchmark adjustments.
    """

    base = get_base_dir()
    cfg = PlayBalanceConfig.from_file(base / "playbalance" / "PBINI.txt")

    if babip_scale_param is not None:
        cfg.babip_scale = babip_scale_param
    if baserunning_aggression is not None:
        cfg.baserunningAggression = baserunning_aggression

    csv_path = base / "data" / "MLB_avg" / "mlb_avg_boxscore_2020_2024_both_teams.csv"
    with csv_path.open(newline="") as f:
        row = next(csv.DictReader(f))

    hits = float(row["Hits"])
    singles = hits - float(row["Doubles"]) - float(row["Triples"]) - float(row["HomeRuns"])
    cfg.hit1BProb = int(round(singles / hits * 100))
    cfg.hit2BProb = int(round(float(row["Doubles"]) / hits * 100))
    cfg.hit3BProb = int(round(float(row["Triples"]) / hits * 100))
    cfg.hitHRProb = max(0, 100 - cfg.hit1BProb - cfg.hit2BProb - cfg.hit3BProb)

    if apply_benchmarks:
        bench_path = base / "data" / "MLB_avg" / "mlb_league_benchmarks_2025_filled.csv"
        with bench_path.open(newline="") as bf:
            benchmarks = {r["metric_key"]: float(r["value"]) for r in csv.DictReader(bf)}

        apply_league_benchmarks(cfg, benchmarks, cfg.babip_scale)

        cfg.swingProbSureStrike = 0.45
        cfg.swingProbCloseStrike = 0.34
        cfg.swingProbCloseBall = 0.24
        cfg.swingProbSureBall = 0.12
        cfg.extraZSwingScale = min(max(cfg.extraZSwingScale, 0.82), 0.90)
        cfg.extraOSwingScale = min(1.04, max(cfg.extraOSwingScale, 1.02))
        cfg.doublePlayProb = min(cfg.doublePlayProb, 0.66)
        cfg.offManStealChancePct = min(max(cfg.offManStealChancePct, 30), 33)
        cfg.baserunningAggression = round(min(max(cfg.baserunningAggression, 0.14), 0.18), 2)
        cfg.stealSuccessBasePct = min(max(cfg.stealSuccessBasePct + 30, 98), 100)
        cfg.stealChanceMedThresh = max(cfg.stealChanceMedThresh, 82)
        cfg.stealChanceFastAdjust = min(cfg.get("stealChanceFastAdjust", 20), 10)
        cfg.stealChanceVeryFastAdjust = min(cfg.get("stealChanceVeryFastAdjust", 25), 14)
        cfg.carryDistanceScale = min(max(cfg.get("carryDistanceScale", 1.0), 1.2), 1.32)
        cfg.carryExitVeloBaseline = min(max(cfg.get("carryExitVeloBaseline", 90.0), 93.0), 95.0)

        cfg.disciplineRatingPct = max(cfg.disciplineRatingPct, 90)
        cfg.swingBallDisciplineWeight = max(cfg.swingBallDisciplineWeight, 0.10)
        cfg.disciplineBallPenalty = max(cfg.disciplineBallPenalty, 0.65)
        cfg.autoTakeDistanceBase = max(cfg.autoTakeDistanceBase, 4.35)
        cfg.autoTakeDistanceBallStep = max(cfg.autoTakeDistanceBallStep, 0.30)
        cfg.autoTakeDistanceMin = max(cfg.autoTakeDistanceMin, 1.5)
        cfg.autoTakeDistanceBuffer = max(cfg.autoTakeDistanceBuffer, 0.05)
        cfg.closeBallDist = max(3, min(getattr(cfg, "closeBallDist", 5), 4))
        cfg.disciplinePenaltyMultiplierDefault = min(
            max(getattr(cfg, "disciplinePenaltyMultiplierDefault", 0.0), 0.30), 0.30
        )
        cfg.values["disciplineRawScaleDefault"] = float(
            min(getattr(cfg, "disciplineRawScaleDefault", 0.95) or 0.95, 0.88)
        )
        cfg.autoTakeThreeBallChaseChance = max(
            getattr(cfg, "autoTakeThreeBallChaseChance", 0.0), 0.68
        )
        cfg.autoTakeDefaultChaseChance = max(
            getattr(cfg, "autoTakeDefaultChaseChance", 0.0), 0.40
        )
        chase_defaults = {
            "00": 0.55,
            "10": 0.60,
            "11": 0.64,
            "12": 0.68,
            "20": 0.72,
            "21": 0.78,
            "22": 0.84,
            "30": 0.86,
            "31": 0.92,
            "32": 0.96,
        }
        for suffix, chance in chase_defaults.items():
            cfg.values[f"autoTakeChaseChance{suffix}"] = float(chance)

        # Apply contact-factor adjustments to curb excessive strikeouts observed
        # in full season simulations. Slightly boosting the contact factor nudges
        # the engine toward league-average strikeout rates.
        base_contact = max(cfg.contactFactorBase, 4.5)
        cfg.contactFactorBase = round(base_contact, 2)
        cfg.contactFactorDiv = max(40, int(round(cfg.contactFactorDiv)))
        cfg.closeBallStrikeBonus = max(cfg.closeBallStrikeBonus, 4)
        cfg.twoStrikeSwingBonus = max(cfg.twoStrikeSwingBonus, 2.6)

        early_swing_adjusts = {
            "swingProb00CountAdjust": -0.18,
            "swingProb01CountAdjust": -0.10,
            "swingProb10CountAdjust": -0.22,
            "swingProb11CountAdjust": -0.08,
            "swingProb20CountAdjust": -0.18,
            "swingProb21CountAdjust": -0.10,
            "swingProb31CountAdjust": 0.30,
            "swingProb32CountAdjust": 0.34,
        }
        for key, value in early_swing_adjusts.items():
            cfg.values[key] = float(value)

        cfg.closeBallTakeBonus = max(getattr(cfg, "closeBallTakeBonus", 0), 1.5)
        cfg.sureBallTakeBonus = max(getattr(cfg, "sureBallTakeBonus", 0), 6.0)
        cfg.disciplinePenaltyFloorOneBall = max(
            getattr(cfg, "disciplinePenaltyFloorOneBall", 0), 0.10
        )
        cfg.disciplinePenaltyFloorTwoBall = max(
            getattr(cfg, "disciplinePenaltyFloorTwoBall", 0), 0.22
        )
        cfg.disciplinePenaltyFloorCap = max(
            getattr(cfg, "disciplinePenaltyFloorCap", 0.0), 0.65
        )
        cfg.closeStrikeDisciplineMix = max(
            getattr(cfg, "closeStrikeDisciplineMix", 0.35), 0.25
        )
        cfg.twoStrikeContactBonus = max(
            getattr(cfg, "twoStrikeContactBonus", 0.0), 1.2
        )
        cfg.twoStrikeContactFloor = max(
            getattr(cfg, "twoStrikeContactFloor", 0.0), 0.04
        )
        cfg.twoStrikeContactQuality = max(
            getattr(cfg, "twoStrikeContactQuality", 0.0), 0.09
        )
        cfg.twoStrikeFoulBonusPct = max(
            getattr(cfg, "twoStrikeFoulBonusPct", 0.0), 14.0
        )

        tuned_overrides = {
            "sureStrikeDist": 2.4,
            "closeStrikeDist": 3.4,
            "closeBallDist": 4.5,
            "swingProbSureStrike": 0.58,
            "swingProbCloseStrike": 0.42,
            "swingProbCloseBall": 0.14,
            "swingProbSureBall": 0.05,
            "contactFactorBase": 5.4,
            "contactFactorDiv": 46,
            "foulPitchBasePct": 26,
            "foulStrikeBasePct": 50,
            "foulProbabilityScale": 1.4,
            "foulBIPBalance": 0.80,
            "twoStrikeContactFloor": 0.78,
            "twoStrikeContactQuality": 0.88,
            "twoStrikeContactBonus": 11.0,
            "twoStrikeSwingBonus": 8.0,
            "twoStrikeChaseBonusScale": 0.05,
            "twoStrikeFoulBonusPct": 96,
            "twoStrikeFoulFloor": 0.24,
            "twoStrikeBIPScale": 0.45,
            "twoStrikeSureSwingFloor": 0.92,
            "twoStrikeCloseSwingFloor": 0.78,
            "twoStrikeChaseSwingFloor": 0.18,
            "missChanceScale": 0.35,
            "contactOutcomeScale": 1.0,
            "maxHitProb": 0.45,
            "foulCountMultiplierDefault": 1.0,
            "foulCountMultiplier00": 1.8,
            "foulCountMultiplier01": 2.5,
            "foulCountMultiplier02": 3.5,
            "foulCountMultiplier10": 2.2,
            "foulCountMultiplier11": 2.8,
            "foulCountMultiplier12": 3.8,
            "foulCountMultiplier20": 2.0,
            "foulCountMultiplier21": 3.0,
            "foulCountMultiplier22": 4.2,
            "foulCountMultiplier30": 0.6,
            "foulCountMultiplier31": 4.2,
            "foulCountMultiplier32": 4.0,
            "swingProb00CountAdjust": 0.08,
            "swingProb01CountAdjust": 0.04,
            "swingProb10CountAdjust": 0.06,
            "swingProb11CountAdjust": 0.03,
            "swingProb12CountAdjust": 0.12,
            "swingProb20CountAdjust": 0.04,
            "swingProb21CountAdjust": 0.01,
            "swingProb22CountAdjust": 0.14,
            "swingProb31CountAdjust": 0.38,
            "swingProb32CountAdjust": 0.44,
            "closeBallTakeBonus": 4.5,
            "sureBallTakeBonus": 12.0,
            "autoTakeDistanceBase": 5.9,
            "autoTakeDistanceBallStep": 0.55,
            "autoTakeDistanceBuffer": 0.45,
            "autoTakeDefaultChaseChance": 0.15,
            "swingBallDisciplineWeight": 0.22,
            "swingZoneDisciplineWeight": 0.18,
            "closeStrikeDisciplineMix": 0.25,
            "plateWidth": 2.9,
            "plateHeight": 2.9,
        }
        for key, value in tuned_overrides.items():
            setattr(cfg, key, value)
            cfg.values[key] = value

        pitcher_obj_overrides = {
            "pitchObj00CountOutsideWeight": 55,
            "pitchObj00CountPlusWeight": 30,
            "pitchObj10CountOutsideWeight": 50,
            "pitchObj10CountPlusWeight": 35,
            "pitchObj20CountOutsideWeight": 50,
            "pitchObj20CountFastCenterWeight": 12,
            "pitchObj11CountOutsideWeight": 42,
            "pitchObj12CountOutsideWeight": 35,
            "pitchObj21CountOutsideWeight": 40,
            "pitchObj22CountOutsideWeight": 32,
        }
        for key, target in pitcher_obj_overrides.items():
            current = cfg.values.get(key, cfg.get(key, 0))
            if "Outside" in key:
                cfg.values[key] = max(current, target)
            else:
                cfg.values[key] = min(current, target)

        # Nudge base hit probability up slightly and relax caps to restore a
        # Major League run environment.
        cfg.hitProbBase = round(cfg.hitProbBase * 1.10, 3)
        cfg.hitProbCap = min(max(cfg.hitProbCap, 0.67), 0.70)
        cfg.contactOutcomeScale = min(
            max(getattr(cfg, "contactOutcomeScale", 1.0), 0.95), 1.0
        )
        cfg.maxHitProb = min(max(cfg.maxHitProb, 0.40), 0.48)

        # Boost batter pitch recognition to curb excessive strikeouts seen in
        # season simulations. Increasing the ease scale makes identifying pitches
        # easier which leads to more contact and fewer swinging strikes.
        cfg.idRatingEaseScale = min(max(cfg.idRatingEaseScale, 2.4), 2.4)
        miss_scale = getattr(cfg, "missChanceScale", 2.05)
        cfg.missChanceScale = max(0.50, round(miss_scale * 0.64, 2))

        # Clean up defensive miscues: bump accuracy/catch baselines and scale throws.
        cfg.catchBaseChance = min(max(cfg.get("catchBaseChance", 70), 65), 78)
        cfg.catchFADiv = max(90, int(cfg.get("catchFADiv", 110) * 0.92))
        cfg.goodThrowBase = min(max(cfg.get("goodThrowBase", 63), 60), 80)
        cfg.goodThrowFAPct = min(max(cfg.get("goodThrowFAPct", 40), 40), 50)
        cfg.throwSuccessScale = min(max(cfg.get("throwSuccessScale", 1.0), 0.98), 1.05)
        cfg.hbpBaseChance = max(0.0, float(cfg.get("hbpBaseChance", 0.0)))
        cfg.hbpBatterStepOutChance = min(max(cfg.get("hbpBatterStepOutChance", 0), 0), 2)

        cfg.collectSwingDiagnostics = int(os.getenv("SWING_DIAGNOSTICS", "0"))

    mlb_averages = {stat: float(val) for stat, val in row.items() if stat}
    return cfg, mlb_averages
