from __future__ import annotations

import random

from .playbalance_config import PlayBalanceConfig


class Physics:
    """Helper performing simple physics related calculations.

    Only a tiny subset of the original game's physics model is reproduced
    here.  The goal is to expose enough behaviour so that unit tests can
    validate that configuration values from :class:`PlayBalanceConfig` influence
    gameplay.  All calculations intentionally stay very small and deterministic
    to keep the tests predictable.
    """

    def __init__(self, config: PlayBalanceConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------
    # Player movement speed
    # ------------------------------------------------------------------
    def player_speed(self, sp: int) -> float:
        """Return the movement speed for a player with ``sp`` rating."""

        base = getattr(self.config, "speedBase")
        pct = getattr(self.config, "speedPct")
        return base + pct * sp / 100.0

    # ------------------------------------------------------------------
    # Bat speed
    # ------------------------------------------------------------------
    def bat_speed(self, ph: int, swing_type: str = "normal") -> float:
        """Return bat speed for ``ph`` and ``swing_type``.

        ``swing_type`` may be ``"power"``, ``"normal"``, ``"contact"`` or
        ``"bunt"``.  Only the adjustment to the PH rating changes between the
        types.  The returned value is expressed in miles per hour just like in
        the original game engine.
        """

        base = getattr(self.config, "swingSpeedBase")
        pct = getattr(self.config, "swingSpeedPHPct")
        adjust_key = {
            "power": "swingSpeedPowerAdjust",
            "normal": "swingSpeedNormalAdjust",
            "contact": "swingSpeedContactAdjust",
            "bunt": "swingSpeedBuntAdjust",
        }.get(swing_type, "swingSpeedNormalAdjust")
        ph_adj = ph + getattr(self.config, adjust_key)
        return base + pct * ph_adj / 100.0

    # ------------------------------------------------------------------
    # Swing angle
    # ------------------------------------------------------------------
    def swing_angle(
        self,
        gf: int,
        *,
        swing_type: str = "normal",
        pitch_loc: str = "middle",
    ) -> float:
        """Return the swing angle in degrees for a player.

        ``gf`` is the batter's ground/fly rating.  ``swing_type`` and
        ``pitch_loc`` can influence the result by applying configuration based
        adjustments.  A deterministic value is returned which keeps unit tests
        simple and reproducible.
        """

        base = getattr(self.config, "swingAngleTenthDegreesBase")
        rng_range = getattr(self.config, "swingAngleTenthDegreesRange")
        # Keep deterministic: use the mid point of the range rather than a
        # random pick.
        angle = base + rng_range / 2.0

        gf_pct = getattr(self.config, "swingAngleTenthDegreesGFPct")
        angle += (gf - 50) * gf_pct / 100.0

        if swing_type == "power":
            angle += getattr(self.config, "swingAngleTenthDegreesPowerAdjust")
        elif swing_type == "contact":
            angle += getattr(self.config, "swingAngleTenthDegreesContactAdjust")

        if pitch_loc == "high":
            angle += getattr(self.config, "swingAngleTenthDegreesHighAdjust")
        elif pitch_loc == "low":
            angle += getattr(self.config, "swingAngleTenthDegreesLowAdjust")
        elif pitch_loc == "outside":
            angle += getattr(self.config, "swingAngleTenthDegreesOutsideAdjust")

        return angle / 10.0


__all__ = ["Physics"]
