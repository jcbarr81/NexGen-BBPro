from __future__ import annotations

from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .simulation import BatterState


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
