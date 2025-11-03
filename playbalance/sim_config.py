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
        cfg.swingProbScale = round(4.5 / pitches_per_pa, 2)
    else:
        cfg.swingProbScale = 1.0
    cfg.swingProbScale = max(cfg.swingProbScale, 1.05)

    z_swing_pct = benchmarks.get("z_swing_pct")
    o_swing_pct = benchmarks.get("o_swing_pct")
    if None not in (z_swing_pct, o_swing_pct):
        base_z = (cfg.swingProbSureStrike + cfg.swingProbCloseStrike) / 2
        base_o = (cfg.swingProbCloseBall + cfg.swingProbSureBall) / 2
        base_z *= cfg.swingProbScale
        base_o *= cfg.swingProbScale
        cfg.zSwingProbScale = round(z_swing_pct / base_z, 2) if base_z else 1.0
        cfg.oSwingProbScale = round(o_swing_pct / base_o, 2) if base_o else 1.0
        cfg.zSwingProbScale = round(
            cfg.zSwingProbScale * cfg.extra_z_swing_scale * 0.96, 2
        )
        cfg.oSwingProbScale = round(
            cfg.oSwingProbScale * cfg.extra_o_swing_scale * 2.10, 2
        )
        cfg.zSwingProbScale = round(min(cfg.zSwingProbScale, 1.04), 2)
        cfg.oSwingProbScale = round(max(cfg.oSwingProbScale, 1.32), 2)

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
        cfg.leagueStrikePct = round(strike_pct * 100 * 1.05, 1)
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

        cfg.swingProbSureStrike = 0.48
        cfg.swingProbCloseStrike = 0.36
        cfg.swingProbCloseBall = 0.22
        cfg.swingProbSureBall = 0.10
        cfg.extraZSwingScale = min(max(cfg.extraZSwingScale, 0.82), 0.90)
        cfg.extraOSwingScale = min(1.04, max(cfg.extraOSwingScale, 1.02))
        cfg.doublePlayProb = min(cfg.doublePlayProb, 0.66)
        cfg.offManStealChancePct = min(max(cfg.offManStealChancePct, 30), 40)
        cfg.baserunningAggression = round(min(max(cfg.baserunningAggression, 0.14), 0.20), 2)
        cfg.stealSuccessBasePct = min(max(cfg.stealSuccessBasePct + 20, 95), 98)
        cfg.stealChanceMedThresh = max(cfg.stealChanceMedThresh, 82)
        cfg.stealChanceFastAdjust = min(cfg.get("stealChanceFastAdjust", 20), 10)
        cfg.stealChanceVeryFastAdjust = min(cfg.get("stealChanceVeryFastAdjust", 25), 14)
        cfg.carryDistanceScale = min(max(cfg.get("carryDistanceScale", 1.0), 1.2), 1.32)
        cfg.carryExitVeloBaseline = min(max(cfg.get("carryExitVeloBaseline", 90.0), 93.0), 95.0)

        cfg.disciplineRatingPct = max(cfg.disciplineRatingPct, 90)
        cfg.swingBallDisciplineWeight = max(cfg.swingBallDisciplineWeight, 0.10)
        cfg.disciplineBallPenalty = max(cfg.disciplineBallPenalty, 0.72)
        cfg.autoTakeDistanceBase = max(cfg.autoTakeDistanceBase, 3.95)
        cfg.autoTakeDistanceBallStep = max(cfg.autoTakeDistanceBallStep, 0.58)
        cfg.autoTakeDistanceMin = max(cfg.autoTakeDistanceMin, 1.6)
        cfg.closeBallDist = max(3, min(getattr(cfg, "closeBallDist", 5), 4))
        cfg.disciplinePenaltyMultiplierDefault = 0.5
        cfg.values["disciplineRawScaleDefault"] = float(
            min(getattr(cfg, "disciplineRawScaleDefault", 0.95) or 0.95, 0.88)
        )
        cfg.autoTakeThreeBallChaseChance = max(
            getattr(cfg, "autoTakeThreeBallChaseChance", 0.0), 0.40
        )
        for suffix, chance in {"21": 0.30, "22": 0.36, "31": 0.54, "32": 0.58}.items():
            cfg.values[f"autoTakeChaseChance{suffix}"] = float(chance)

        # Apply contact-factor adjustments to curb excessive strikeouts observed
        # in full season simulations. Slightly boosting the contact factor nudges
        # the engine toward league-average strikeout rates.
        base_contact = max(cfg.contactFactorBase, 1.62)
        cfg.contactFactorBase = round(base_contact * 1.18, 2)
        cfg.contactFactorDiv = max(96, int(round(cfg.contactFactorDiv * 0.86)))
        cfg.closeBallStrikeBonus = max(cfg.closeBallStrikeBonus, 0)
        cfg.twoStrikeSwingBonus = max(cfg.twoStrikeSwingBonus, 5)

        # Nudge base hit probability up slightly and relax caps to restore a
        # Major League run environment.
        cfg.hitProbBase = round(cfg.hitProbBase * 1.0, 3)
        cfg.hitProbCap = min(max(cfg.hitProbCap, 0.67), 0.70)
        cfg.contactOutcomeScale = min(
            max(getattr(cfg, "contactOutcomeScale", 0.9), 0.9), 0.95
        )
        cfg.maxHitProb = min(max(cfg.maxHitProb, 0.38), 0.40)

        # Boost batter pitch recognition to curb excessive strikeouts seen in
        # season simulations. Increasing the ease scale makes identifying pitches
        # easier which leads to more contact and fewer swinging strikes.
        cfg.idRatingEaseScale = min(max(cfg.idRatingEaseScale, 1.44), 1.78)
        miss_scale = getattr(cfg, "missChanceScale", 2.05)
        cfg.missChanceScale = min(1.5, max(1.25, round(miss_scale * 0.76, 2)))

        # Clean up defensive miscues: bump accuracy/catch baselines and scale throws.
        cfg.catchBaseChance = min(max(cfg.get("catchBaseChance", 70), 78), 85)
        cfg.catchFADiv = max(90, int(cfg.get("catchFADiv", 110) * 0.92))
        cfg.goodThrowBase = min(max(cfg.get("goodThrowBase", 63), 78), 88)
        cfg.goodThrowFAPct = min(max(cfg.get("goodThrowFAPct", 40), 48), 60)
        cfg.throwSuccessScale = min(max(cfg.get("throwSuccessScale", 1.0), 1.12), 1.2)
        cfg.hbpBaseChance = max(cfg.get("hbpBaseChance", 0.0), 0.15)
        cfg.hbpBatterStepOutChance = min(cfg.get("hbpBatterStepOutChance", 18), 2)

        cfg.collectSwingDiagnostics = int(os.getenv("SWING_DIAGNOSTICS", "0"))

    mlb_averages = {stat: float(val) for stat, val in row.items() if stat}
    return cfg, mlb_averages
