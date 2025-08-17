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

    # ------------------------------------------------------------------
    # Ball physics
    # ------------------------------------------------------------------
    def ball_roll_distance(
        self,
        initial_speed: float,
        surface: str = "grass",
        *,
        altitude: float = 0.0,
        temperature: float = 70.0,
        wind_speed: float = 0.0,
    ) -> float:
        """Return the roll distance for a ball given the environment.

        The calculation intentionally keeps the numbers small and deterministic.
        Configuration entries from :class:`PlayBalanceConfig` influence the
        result.  ``surface`` may be ``"grass"`` or ``"turf"`` which selects the
        appropriate friction factor.
        """

        friction_key = f"rollFriction{surface.capitalize()}"
        friction = getattr(self.config, friction_key)
        distance = initial_speed / max(1.0, friction)

        air = getattr(self.config, "ballAirResistancePct")
        distance *= air / 100.0

        alt_pct = getattr(self.config, "ballAltitudePct")
        base_alt = getattr(self.config, "ballBaseAltitude")
        distance += distance * ((altitude + base_alt) * alt_pct) / 100000.0

        temp_pct = getattr(self.config, "ballTempPct")
        distance += distance * ((temperature - 70.0) * temp_pct) / 1000.0

        wind_pct = getattr(self.config, "ballWindSpeedPct")
        distance += distance * (wind_speed * wind_pct) / 1000.0

        return max(0.0, distance)

    def ball_bounce(
        self,
        vert_speed: float,
        horiz_speed: float,
        surface: str = "grass",
        *,
        wet: bool = False,
        temperature: float = 70.0,
    ) -> tuple[float, float]:
        """Return the vertical and horizontal bounce speeds for the ball.

        ``surface`` may be ``"grass"``, ``"turf"`` or ``"dirt"``.  ``wet`` and
        ``temperature`` apply additional modifiers.  The returned tuple contains
        the resulting vertical and horizontal speeds after the bounce.
        """

        vert_key = f"bounceVert{surface.capitalize()}Pct"
        horiz_key = f"bounceHoriz{surface.capitalize()}Pct"
        vert_pct = getattr(self.config, vert_key)
        horiz_pct = getattr(self.config, horiz_key)

        adjust = 0.0
        if wet:
            adjust += getattr(self.config, "bounceWetAdjust")
        if temperature >= 85:
            adjust += getattr(self.config, "bounceHotAdjust")
        elif temperature <= 50:
            adjust += getattr(self.config, "bounceColdAdjust")

        vert_pct = max(0.0, vert_pct + adjust)
        horiz_pct = max(0.0, horiz_pct + adjust)

        return (
            vert_speed * vert_pct / 100.0,
            horiz_speed * horiz_pct / 100.0,
        )


__all__ = ["Physics"]
