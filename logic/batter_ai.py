"""Simplified batter AI used by the tests.

The real engine contains a complex batter decision system considering pitch
location, pitch type recognition and count specific adjustments.  The goal of
this module is not to reproduce that behaviour exactly but to expose a minimal
subset that allows unit tests to verify that values from :class:`PlayBalance`
configuration influence swing decisions and contact quality.

Only a handful of options are supported:

``sureStrikeDist``
    Distance from the centre of the strike zone that is considered a guaranteed
    strike.  The simulation currently assumes all pitches have a distance of
    ``0`` but the value still influences strike detection when calling the AI
    directly in tests.

``lookPrimaryTypeXXCountAdjust``
    Count specific adjustment applied when the batter is looking for the
    pitcher's primary pitch.  ``XX`` represents the current ``balls`` and
    ``strikes`` count.  When the pitched type matches and the batter is looking
    for the primary pitch the adjustment increases the chance to correctly
    identify the pitch.

``idRatingBase``
    Base chance in percent to correctly identify the pitch type.  Higher values
    improve both swing decisions and contact quality.

The :class:`BatterAI` exposes :func:`decide_swing` which returns a tuple of
``(swing, contact_quality)``.  ``swing`` determines whether the batter offers at
        the pitch.  ``contact_quality`` is a multiplier in the range ``0.0`` to
``1.0`` that represents the quality of the swing timing.  Tests and the game
loop can use this value to influence hit probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from models.player import Player
from models.pitcher import Pitcher
from .playbalance_config import PlayBalanceConfig

# Ordering of pitch ratings on the :class:`~models.pitcher.Pitcher` model.  This
# mirrors the constant used by :mod:`logic.pitcher_ai` but is duplicated here to
# keep the modules independent.
_PITCH_RATINGS = ["fb", "sl", "cu", "cb", "si", "scb", "kn"]


@dataclass
class BatterAI:
    """Very small helper encapsulating batter decision making."""

    config: PlayBalanceConfig

    # Cache of primary pitch type per pitcher
    _primary_cache: Dict[str, str] = None  # type: ignore[assignment]

    # Last ``(swing, contact_quality)`` decision made.  Useful for tests.
    last_decision: Tuple[bool, float] | None = None

    def __post_init__(self) -> None:  # pragma: no cover - simple initialiser
        if self._primary_cache is None:
            self._primary_cache = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _primary_pitch(self, pitcher: Pitcher) -> str:
        pid = pitcher.player_id
        if pid not in self._primary_cache:
            ratings = {p: getattr(pitcher, p) for p in _PITCH_RATINGS}
            primary = max(ratings.items(), key=lambda kv: kv[1])[0]
            self._primary_cache[pid] = primary
        return self._primary_cache[pid]

    # ------------------------------------------------------------------
    # Decision making
    # ------------------------------------------------------------------
    def pitch_class(self, dist: int) -> str:
        """Return pitch classification based on distance from the zone centre."""

        sure_strike = self.config.get("sureStrikeDist", 3)
        close_strike = self.config.get("closeStrikeDist", sure_strike + 1)
        close_ball = self.config.get("closeBallDist", close_strike + 1)

        if dist <= sure_strike:
            return "sure strike"
        if dist <= close_strike:
            return "close strike"
        if dist <= close_ball:
            return "close ball"
        return "sure ball"

    # ------------------------------------------------------------------
    # Main decision method
    # ------------------------------------------------------------------
    def decide_swing(
        self,
        batter: Player,
        pitcher: Pitcher,
        *,
        pitch_type: str,
        balls: int = 0,
        strikes: int = 0,
        dist: int = 0,
        random_value: float = 0.0,
    ) -> Tuple[bool, float]:
        """Return ``(swing, contact_quality)`` for the next pitch.

        ``random_value`` is expected to be a floating point value in the range
        ``[0.0, 1.0)`` and is typically supplied by the caller to keep the number
        of RNG rolls deterministic for the tests.
        """

        p_class = self.pitch_class(dist)
        is_strike = p_class in {"sure strike", "close strike"}

        # Chance to correctly identify the pitch type
        id_base = self.config.get("idRatingBase", 0)
        primary = self._primary_pitch(pitcher)
        look_key = f"lookPrimaryType{balls}{strikes}CountAdjust"
        adjust = self.config.get(look_key, 0) if pitch_type == primary else 0
        id_chance = max(0.0, min(1.0, (id_base + adjust) / 100.0))
        identified = random_value < id_chance

        if identified:
            swing = is_strike
        else:
            swing_probs = {
                "sure strike": 0.75,
                "close strike": 0.5,
                "close ball": 0.25,
                "sure ball": 0.0,
            }
            swing = random_value < swing_probs[p_class]

        contact = 1.0 if identified else 0.5 if swing else 0.0
        self.last_decision = (swing, contact)
        return self.last_decision


__all__ = ["BatterAI"]
