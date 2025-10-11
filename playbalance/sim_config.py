from __future__ import annotations

"""Helpers for loading and tuning :class:`PlayBalanceConfig`."""

import csv
from typing import Tuple, Dict

from .playbalance_config import PlayBalanceConfig
from utils.path_utils import get_base_dir

# Scaling factor applied to outs on balls in play to tune the simulated
# batting average on balls in play (BABIP). Values below ``1`` decrease outs
# and raise BABIP, values above ``1`` increase outs and lower BABIP. ``1.0``
# uses the MLB averages without additional adjustment.
_BABIP_OUT_ADJUST = 1.0


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
    cfg.ballInPlayPitchPct = int(round(pip_pct * 100)) - 1
    pitches_per_pa = benchmarks["pitches_per_pa"]
    if pitches_per_pa:
        cfg.swingProbScale = round(4.0 / pitches_per_pa, 2)
    else:
        cfg.swingProbScale = 1.0

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
        cfg.leagueStrikePct = round(strike_pct * 100, 1)
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

        cfg.swingProbSureStrike = round(cfg.swingProbSureStrike * 1.04, 2)
        cfg.swingProbCloseStrike = round(cfg.swingProbCloseStrike * 1.06, 2)
        cfg.swingProbCloseBall = round(cfg.swingProbCloseBall * 1.25, 2)
        cfg.swingProbSureBall = round(cfg.swingProbSureBall * 1.45, 2)
        cfg.extraZSwingScale = min(cfg.extraZSwingScale, 0.98)
        cfg.extraOSwingScale = max(cfg.extraOSwingScale, 1.55)
        cfg.doublePlayProb = min(cfg.doublePlayProb, 0.74)
        cfg.offManStealChancePct = max(cfg.offManStealChancePct, 115)
        cfg.stealSuccessBasePct = max(cfg.stealSuccessBasePct, 86)
        cfg.stealChanceMedThresh = min(cfg.stealChanceMedThresh, 52)
        cfg.carryDistanceScale = max(cfg.get("carryDistanceScale", 1.0), 2.1)
        cfg.carryExitVeloBaseline = max(cfg.get("carryExitVeloBaseline", 90.0), 95.0)

        # Apply contact-factor adjustments to curb excessive strikeouts observed
        # in full season simulations. Slightly boosting the contact factor nudges
        # the engine toward league-average strikeout rates.
        cfg.contactFactorBase = round(cfg.contactFactorBase * 1.04, 2)
        cfg.contactFactorDiv = int(cfg.contactFactorDiv * 0.94)
        cfg.closeBallStrikeBonus = max(cfg.closeBallStrikeBonus, 2)
        cfg.twoStrikeSwingBonus = max(cfg.twoStrikeSwingBonus, 8)

        # Boost batter pitch recognition to curb excessive strikeouts seen in
        # season simulations. Increasing the ease scale makes identifying pitches
        # easier which leads to more contact and fewer swinging strikes.
        cfg.idRatingEaseScale = 3.0

    mlb_averages = {stat: float(val) for stat, val in row.items() if stat}
    return cfg, mlb_averages
