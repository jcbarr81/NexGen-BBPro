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
    # Pitch velocity
    # ------------------------------------------------------------------
    def pitch_velocity(
        self, pitch_type: str, as_rating: int, *, rand: float | None = None
    ) -> float:
        """Return the pitch speed for ``pitch_type`` and ``as_rating``.

        The calculation mirrors the original game's behaviour by combining
        ``{pitch}SpeedBase``, ``{pitch}SpeedRange`` and ``{pitch}SpeedASPct``
        configuration entries.  ``rand`` allows tests to supply a deterministic
        random value; when omitted the RNG associated with this instance is
        used.
        """

        key_map = {"kn": "kb", "scb": "sb"}
        key = key_map.get(pitch_type.lower(), pitch_type.lower())
        base = getattr(self.config, f"{key}SpeedBase")
        rng_range = getattr(self.config, f"{key}SpeedRange")
        pct = getattr(self.config, f"{key}SpeedASPct")
        if rand is None:
            rand = self.rng.random()
        return base + rand * rng_range + as_rating * pct / 100.0

    # ------------------------------------------------------------------
    # Bat speed
    # ------------------------------------------------------------------
    def bat_speed(
        self,
        ph: int,
        swing_type: str = "normal",
        *,
        pitch_speed: float | None = None,
    ) -> float:
        """Return bat speed for ``ph`` and ``swing_type``.

        ``swing_type`` may be ``"power"``, ``"normal"``, ``"contact"`` or
        ``"bunt"``.  Only the adjustment to the PH rating changes between the
        types.  The returned value is expressed in miles per hour just like in
        the original game engine.

        ``pitch_speed`` represents the speed of the incoming pitch.  When
        provided, the value is compared to the configured
        ``averagePitchSpeed``.  Pitches faster than the average reduce the
        resulting bat speed while slower pitches increase it.
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
        speed = base + pct * ph_adj / 100.0

        if pitch_speed is None:
            return speed

        avg = getattr(self.config, "averagePitchSpeed")
        diff = pitch_speed - avg
        if diff > 0:
            slowdown = getattr(self.config, "fastPitchBatSlowdownPct")
            speed -= diff * slowdown / 100.0
        elif diff < 0:
            speedup = getattr(self.config, "slowPitchBatSpeedupPct")
            speed += (-diff) * speedup / 100.0

        return speed

    # ------------------------------------------------------------------
    # Bat impact
    # ------------------------------------------------------------------
    def bat_impact(
        self,
        bat_speed: float,
        *,
        rand: float | None = None,
        part: str | None = None,
    ) -> tuple[float, str]:
        """Return adjusted ``bat_speed`` based on contact point on the bat.

        A bat can be struck with four distinct parts: ``"handle"``,
        ``"dull"``, ``"sweet``" and ``"end"``.  Each part has a configured base
        power percentage and optional random variation range.  When ``part`` is
        not supplied it is chosen based on ``rand``.  The final power is the
        bat speed scaled by ``batPower{Part}Base`` plus a variation within
        ``batPower{Part}Range``.  The adjusted speed and the selected part are
        returned.
        """

        parts = ["handle", "dull", "sweet", "end"]
        if part is None:
            if rand is None:
                rand = self.rng.random()
            idx = int(rand * len(parts))
            part = parts[idx]
            frac = rand * len(parts) - idx
        else:
            if rand is None:
                rand = self.rng.random()
            frac = rand

        base = getattr(self.config, f"batPower{part.capitalize()}Base")
        rng_range = getattr(self.config, f"batPower{part.capitalize()}Range")
        pct = base + (frac * 2 - 1) * rng_range
        return bat_speed * pct / 100.0, part

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

        ``gf`` is the batter's ground/fly rating. ``swing_type`` and
        ``pitch_loc`` can influence the result by applying configuration based
        adjustments. The angle is randomized within the configured range using
        the RNG supplied to :class:`Physics`. Supplying a seeded RNG keeps unit
        tests reproducible.
        """

        base = getattr(self.config, "swingAngleTenthDegreesBase")
        rng_range = getattr(self.config, "swingAngleTenthDegreesRange")
        angle = self.rng.uniform(base, base + rng_range) if rng_range else base

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
    # Vertical hit angle
    # ------------------------------------------------------------------
    def vertical_hit_angle(self, swing_type: str = "normal") -> float:
        """Return vertical launch angle offset for ``swing_type``.

        The original game determines the vertical angle of the ball off the bat
        by rolling a configurable number of dice.  Each swing type uses its own
        ``hitAngleCount*``, ``hitAngleFaces*`` and ``hitAngleBase*`` values from
        :class:`PlayBalanceConfig`.  The dice results are summed, adjusted by the
        base value and then converted into an angle between ``-90`` and ``+90``
        degrees.  Values below ``1`` or above ``59`` are clamped to the nearest
        valid range before conversion.
        """

        cap = swing_type.capitalize()
        count = getattr(self.config, f"hitAngleCount{cap}")
        faces = getattr(self.config, f"hitAngleFaces{cap}")
        base = getattr(self.config, f"hitAngleBase{cap}")

        roll = base
        for _ in range(max(0, count)):
            roll += self.rng.randint(1, max(1, faces))

        roll = max(1, min(59, roll))
        return (roll - 30) * (180.0 / 58.0)

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
