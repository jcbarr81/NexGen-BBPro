from __future__ import annotations

from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .simulation import BatterState, PitcherState, FieldingState


def compute_batting_derived(stats: 'BatterState') -> Dict[str, float]:
    """Return derived batting statistics from counting stats.

    Parameters
    ----------
    stats: BatterState
        The batter statistics to derive from.
    """
    tb = stats.b1 + 2 * stats.b2 + 3 * stats.b3 + 4 * stats.hr
    xbh = stats.b2 + stats.b3 + stats.hr
    lob = stats.lob
    p_pa = stats.pitches / stats.pa if stats.pa else 0.0
    return {"tb": tb, "xbh": xbh, "lob": lob, "p_pa": p_pa}


def compute_batting_rates(stats: 'BatterState') -> Dict[str, float]:
    """Return rate-based batting metrics."""
    derived = compute_batting_derived(stats)
    ab = stats.ab
    pa = stats.pa
    h = stats.h
    bb = stats.bb
    hbp = stats.hbp
    sf = stats.sf
    tb = derived["tb"]

    avg = h / ab if ab else 0.0
    obp_den = ab + bb + hbp + sf
    obp = (h + bb + hbp) / obp_den if obp_den else 0.0
    slg = tb / ab if ab else 0.0
    ops = obp + slg
    iso = slg - avg
    babip_den = ab - stats.hr - stats.so + sf
    babip = (h - stats.hr) / babip_den if babip_den else 0.0
    bb_pct = bb / pa if pa else 0.0
    k_pct = stats.so / pa if pa else 0.0
    bb_k = bb / stats.so if stats.so else 0.0
    sb_den = stats.sb + stats.cs
    sb_pct = stats.sb / sb_den if sb_den else 0.0

    return {
        "avg": avg,
        "obp": obp,
        "slg": slg,
        "ops": ops,
        "iso": iso,
        "babip": babip,
        "bb_pct": bb_pct,
        "k_pct": k_pct,
        "bb_k": bb_k,
        "sb_pct": sb_pct,
    }


def compute_pitching_derived(stats: 'PitcherState') -> Dict[str, float]:
    """Return derived pitching statistics from counting stats."""

    ip = stats.outs / 3.0
    cg = 1 if stats.gs and stats.gf and stats.outs >= 27 else 0
    sho = 1 if cg and stats.r == 0 else 0
    qs = 1 if stats.gs and stats.outs >= 18 and stats.er <= 3 else 0
    k_minus_bb = stats.so - stats.bb
    return {
        "ip": ip,
        "cg": cg,
        "sho": sho,
        "qs": qs,
        "k_minus_bb": k_minus_bb,
    }


def compute_pitching_rates(stats: 'PitcherState') -> Dict[str, float]:
    """Return rate-based pitching metrics."""

    ip = stats.outs / 3.0
    h9 = (stats.h * 9 / ip) if ip else 0.0
    hr9 = (stats.hr * 9 / ip) if ip else 0.0
    k9 = (stats.so * 9 / ip) if ip else 0.0
    bb9 = (stats.bb * 9 / ip) if ip else 0.0
    era = (stats.er * 9 / ip) if ip else 0.0
    whip = ((stats.bb + stats.h) / ip) if ip else 0.0
    k_bb = (stats.so / stats.bb) if stats.bb else 0.0
    fip = (
        ((13 * stats.hr) + 3 * (stats.bb + stats.hbp) - 2 * stats.so) / ip + 3.2
        if ip
        else 0.0
    )
    lob_den = stats.h + stats.bb + stats.hbp - 1.4 * stats.hr
    lob_pct = (
        (stats.h + stats.bb + stats.hbp - stats.r) / lob_den if lob_den else 0.0
    )
    fps_pct = stats.first_pitch_strikes / stats.bf if stats.bf else 0.0
    zone_pct = stats.zone_pitches / stats.pitches_thrown if stats.pitches_thrown else 0.0
    z_swing_pct = stats.zone_swings / stats.zone_pitches if stats.zone_pitches else 0.0
    z_contact_pct = (
        stats.zone_contacts / stats.zone_swings if stats.zone_swings else 0.0
    )
    o_zone_pitches = stats.pitches_thrown - stats.zone_pitches
    ozone_swing_pct = (
        stats.o_zone_swings / o_zone_pitches if o_zone_pitches else 0.0
    )
    ozone_contact_pct = (
        stats.o_zone_contacts / stats.o_zone_swings if stats.o_zone_swings else 0.0
    )
    ozone_pct = o_zone_pitches / stats.pitches_thrown if stats.pitches_thrown else 0.0

    return {
        "h9": h9,
        "hr9": hr9,
        "k9": k9,
        "bb9": bb9,
        "era": era,
        "whip": whip,
        "k_bb": k_bb,
        "fip": fip,
        "lob_pct": lob_pct,
        "fps_pct": fps_pct,
        "zone_pct": zone_pct,
        "z_swing_pct": z_swing_pct,
        "z_contact_pct": z_contact_pct,
        "ozone_pct": ozone_pct,
        "ozone_swing_pct": ozone_swing_pct,
        "ozone_contact_pct": ozone_contact_pct,
    }


def compute_fielding_derived(stats: 'FieldingState') -> Dict[str, float]:
    """Return derived fielding totals."""

    tc = stats.po + stats.a + stats.e
    of_a = stats.a if stats.player.primary_position in {"LF", "CF", "RF"} else 0
    return {"tc": tc, "of_a": of_a}


def compute_fielding_rates(stats: 'FieldingState') -> Dict[str, float]:
    """Return rate-based fielding metrics."""

    tc = stats.po + stats.a + stats.e
    fpct = (stats.po + stats.a) / tc if tc else 0.0
    total_play = stats.po + stats.a
    rf9 = total_play / stats.g if stats.g else 0.0
    rfg = total_play / stats.g if stats.g else 0.0
    cs_pct = stats.cs / stats.sba if stats.sba else 0.0
    pb_g = stats.pb / stats.g if stats.g else 0.0
    return {
        "fpct": fpct,
        "rf9": rf9,
        "rfg": rfg,
        "cs_pct": cs_pct,
        "pb_g": pb_g,
    }
