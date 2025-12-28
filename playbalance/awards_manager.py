"""Utilities for determining end-of-season awards.

This module provides simple helpers that select award winners based on
season statistics.  The goal is not to perfectly emulate real-world award
voting but to offer a deterministic way to highlight top performers.

Example
-------
>>> manager = AwardsManager(players, batting_stats, pitching_stats)
>>> manager.select_award_winners()
{"MVP": Player(...), "CY_YOUNG": Player(...)}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from models.player import Player


@dataclass
class AwardWinner:
    """Container storing the winning player and their key metric."""

    player: Player
    metric: float


class AwardsManager:
    """Select season awards based on provided statistics.

    Parameters
    ----------
    players:
        Mapping of player identifiers to :class:`~models.player.Player`
        instances.
    batting_stats:
        Statistics keyed by player identifier containing at minimum an
        ``"ops"`` value.
    pitching_stats:
        Statistics keyed by player identifier containing at minimum an
        ``"era"`` value.
    """

    def __init__(
        self,
        players: Mapping[str, Player],
        batting_stats: Mapping[str, Mapping[str, float]],
        pitching_stats: Mapping[str, Mapping[str, float]],
        *,
        min_pa: int = 0,
        min_ip: float = 0.0,
    ) -> None:
        self.players = players
        self.batting_stats = batting_stats
        self.pitching_stats = pitching_stats
        self.min_pa = max(0, int(min_pa))
        self.min_ip = float(min_ip or 0.0)

    # ------------------------------------------------------------------
    # Award selection helpers
    # ------------------------------------------------------------------
    def select_mvp(self) -> AwardWinner:
        """Return the Most Valuable Player based on OPS."""

        if not self.batting_stats:
            raise ValueError("No batting statistics provided")
        pool = self._qualifying_batters()
        if not pool:
            pool = dict(self.batting_stats)
        winner_id = max(pool, key=lambda pid: self._ops(pool[pid]))
        metric = self._ops(pool[winner_id])
        return AwardWinner(self.players[winner_id], metric)

    def select_cy_young(self) -> AwardWinner:
        """Return the top pitcher based on ERA."""

        if not self.pitching_stats:
            raise ValueError("No pitching statistics provided")
        pool = self._qualifying_pitchers()
        if not pool:
            pool = dict(self.pitching_stats)
        winner_id = min(pool, key=lambda pid: self._era(pool[pid]))
        metric = self._era(pool[winner_id])
        return AwardWinner(self.players[winner_id], metric)

    def select_award_winners(self) -> Dict[str, AwardWinner]:
        """Return a dictionary of award names mapped to winners."""

        return {
            "MVP": self.select_mvp(),
            "CY_YOUNG": self.select_cy_young(),
        }

    def _qualifying_batters(self) -> Dict[str, Mapping[str, float]]:
        if self.min_pa <= 0:
            return dict(self.batting_stats)
        return {
            pid: stats
            for pid, stats in self.batting_stats.items()
            if self._batter_pa(stats) >= self.min_pa
        }

    def _qualifying_pitchers(self) -> Dict[str, Mapping[str, float]]:
        if self.min_ip <= 0:
            return dict(self.pitching_stats)
        return {
            pid: stats
            for pid, stats in self.pitching_stats.items()
            if self._pitcher_ip(stats) >= self.min_ip
        }

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _batter_pa(self, stats: Mapping[str, float]) -> float:
        pa = stats.get("pa")
        if pa is not None:
            return self._safe_float(pa)
        ab = self._safe_float(stats.get("ab"))
        bb = self._safe_float(stats.get("bb"))
        hbp = self._safe_float(stats.get("hbp"))
        sf = self._safe_float(stats.get("sf"))
        ci = self._safe_float(stats.get("ci"))
        return ab + bb + hbp + sf + ci

    def _pitcher_ip(self, stats: Mapping[str, float]) -> float:
        ip = stats.get("ip")
        if ip is not None:
            return self._safe_float(ip)
        outs = stats.get("outs")
        if outs is None:
            return 0.0
        return self._safe_float(outs) / 3.0

    def _ops(self, stats: Mapping[str, float]) -> float:
        ops = stats.get("ops")
        if ops is not None:
            return self._safe_float(ops)
        ab = self._safe_float(stats.get("ab"))
        h = self._safe_float(stats.get("h"))
        bb = self._safe_float(stats.get("bb"))
        hbp = self._safe_float(stats.get("hbp"))
        sf = self._safe_float(stats.get("sf"))
        b2 = self._safe_float(stats.get("b2", stats.get("2b", 0.0)))
        b3 = self._safe_float(stats.get("b3", stats.get("3b", 0.0)))
        hr = self._safe_float(stats.get("hr"))
        singles = max(0.0, h - b2 - b3 - hr)
        total_bases = singles + 2 * b2 + 3 * b3 + 4 * hr
        obp_den = ab + bb + hbp + sf
        obp = (h + bb + hbp) / obp_den if obp_den else 0.0
        slg = total_bases / ab if ab else 0.0
        return obp + slg

    def _era(self, stats: Mapping[str, float]) -> float:
        era = stats.get("era")
        if era is not None:
            return self._safe_float(era, default=float("inf"))
        ip = self._pitcher_ip(stats)
        if ip <= 0:
            return float("inf")
        er = self._safe_float(stats.get("er"))
        return (er * 9.0) / ip
