from __future__ import annotations

import math
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
    # Fielder reaction delay
    # ------------------------------------------------------------------
    def reaction_delay(self, position: str, fa: int) -> float:
        """Return the reaction delay for a fielder."""

        suffix_map = {
            "P": "Pitcher",
            "C": "Catcher",
            "1B": "FirstBase",
            "2B": "SecondBase",
            "3B": "ThirdBase",
            "SS": "ShortStop",
            "LF": "LeftField",
            "CF": "CenterField",
            "RF": "RightField",
        }
        suffix = suffix_map.get(position.upper())
        if suffix is None:
            return 0.0
        base = getattr(self.config, f"delayBase{suffix}")
        pct = getattr(self.config, f"delayFAPct{suffix}")
        return base + pct * fa / 100.0

    # ------------------------------------------------------------------
    # Fielder throw calculations
    # ------------------------------------------------------------------
    def max_throw_distance(self, as_rating: int) -> float:
        """Return maximum throw distance for ``as_rating`` arm strength."""

        base = getattr(self.config, "maxThrowDistBase")
        pct = getattr(self.config, "maxThrowDistASPct")
        return base + pct * as_rating / 100.0

    def throw_velocity(self, distance: float, *, outfield: bool) -> float:
        """Return throw velocity for ``distance`` and fielder type."""

        prefix = "OF" if outfield else "IF"
        base = getattr(self.config, f"throwSpeed{prefix}Base")
        pct = getattr(self.config, f"throwSpeed{prefix}DistPct")
        max_speed = getattr(self.config, f"throwSpeed{prefix}Max")
        speed = base + pct * distance / 100.0
        return min(speed, max_speed)

    def throw_time(self, as_rating: int, distance: float, position: str) -> float:
        """Return travel time for a throw to cover ``distance`` feet."""

        max_dist = self.max_throw_distance(as_rating)
        if distance > max_dist:
            return float("inf")
        outfield = position.upper() in {"LF", "CF", "RF"}
        speed = self.throw_velocity(distance, outfield=outfield)
        fps = speed * 5280 / 3600
        if fps <= 0:
            return float("inf")
        return distance / fps

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
    # Pitch control box
    # ------------------------------------------------------------------
    def control_box(self, pitch_type: str) -> tuple[int, int]:
        """Return ``(width, height)`` of the control box for ``pitch_type``.

        Control boxes define the horizontal and vertical area a pitch may land
        in when the pitcher has perfect control.  Values are sourced from
        ``{pitch}ControlBoxWidth`` and ``{pitch}ControlBoxHeight`` entries in
        :class:`PlayBalanceConfig`.  Pitch types that are aliases of the
        configuration keys (e.g. ``kn`` -> ``kb``) are resolved automatically.
        """

        key_map = {"kn": "kb", "scb": "sb"}
        key = key_map.get(pitch_type.lower(), pitch_type.lower())
        width = getattr(self.config, f"{key}ControlBoxWidth")
        height = getattr(self.config, f"{key}ControlBoxHeight")
        return width, height

    # ------------------------------------------------------------------
    # Missed control adjustments
    # ------------------------------------------------------------------
    def expand_control_box(
        self, width: float, height: float, miss_amt: float
    ) -> tuple[float, float]:
        """Return increased control box dimensions for a missed control check.

        ``miss_amt`` is the amount the control check was missed by, expressed
        on a 0-100 scale. ``controlBoxIncreaseEffCOPct`` determines how many
        squares are added to both width and height.
        """

        inc_pct = getattr(self.config, "controlBoxIncreaseEffCOPct")
        increase = miss_amt * inc_pct / 100.0
        return width + increase, height + increase

    def reduce_pitch_velocity_for_miss(
        self, pitch_speed: float, miss_amt: float, *, rand: float | None = None
    ) -> float:
        """Return ``pitch_speed`` adjusted for a missed control check."""

        base = getattr(self.config, "speedReductionBase")
        rng_range = getattr(self.config, "speedReductionRange")
        eff_pct = getattr(self.config, "speedReductionEffMOPct")
        if rand is None:
            rand = self.rng.random()
        rand_int = int(rand * (rng_range + 1))
        reduction = base + rand_int + miss_amt * eff_pct / 100.0
        return max(0.0, pitch_speed - reduction)

    # ------------------------------------------------------------------
    # Pitch break
    # ------------------------------------------------------------------
    def pitch_break(self, pitch_type: str, *, rand: float | None = None) -> tuple[float, float]:
        """Return ``(dx, dy)`` break offsets for ``pitch_type``.

        The offsets are derived from ``{pitch}BreakBaseWidth`` /
        ``{pitch}BreakBaseHeight`` and their corresponding ``BreakRange``
        entries in :class:`PlayBalanceConfig`.  ``rand`` allows tests to supply
        a deterministic random value.  When omitted the RNG associated with
        this instance is used.  The same random value influences both axes to
        keep the number of RNG calls predictable for the simulation.
        """

        key_map = {"kn": "kb", "scb": "sb"}
        key = key_map.get(pitch_type.lower(), pitch_type.lower())
        base_w = getattr(self.config, f"{key}BreakBaseWidth")
        base_h = getattr(self.config, f"{key}BreakBaseHeight")
        range_w = getattr(self.config, f"{key}BreakRangeWidth")
        range_h = getattr(self.config, f"{key}BreakRangeHeight")
        if rand is None:
            rand = self.rng.random()
        dx = base_w + rand * range_w
        dy = base_h + rand * range_h
        return dx, dy

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

    # ------------------------------------------------------------------
    # Batted ball trajectory helpers
    # ------------------------------------------------------------------
    def launch_vector(
        self,
        ph: int,
        pl: int,
        swing_angle: float,
        vertical_hit_angle: float,
    ) -> tuple[float, float, float]:
        """Return velocity components for a batted ball.

        ``ph`` is the batter's power rating and ``pl`` their pull tendency.
        ``swing_angle`` represents the angle of the bat through the zone while
        ``vertical_hit_angle`` is the rolled launch angle offset.  Both angles
        are combined with a power based adjustment allowing strong hitters to
        generate higher trajectories.  The calculation keeps the numbers small
        and deterministic and is not a realistic model of actual exit
        velocities.
        """

        speed_mph = 50 + ph * 0.5
        speed_fps = speed_mph * 5280 / 3600

        power_adjust = (ph - 50) * 0.1
        vert_angle = swing_angle + vertical_hit_angle + power_adjust
        horiz_angle = -45 + pl * 0.9

        v_rad = math.radians(vert_angle)
        h_rad = math.radians(horiz_angle)

        vx = speed_fps * math.cos(v_rad) * math.cos(h_rad)
        vy = speed_fps * math.cos(v_rad) * math.sin(h_rad)
        vz = speed_fps * math.sin(v_rad)
        return vx, vy, vz

    def landing_point(
        self, vx: float, vy: float, vz: float, *, height: float = 3.0
    ) -> tuple[float, float, float]:
        """Return ``(x, y, t)`` where the ball lands.

        ``height`` represents the initial height of the ball off the bat in
        feet.  Air resistance is ignored and the ball is assumed to be
        influenced only by gravity.
        """

        g = 32.174
        t = (vz + math.sqrt(max(0.0, vz * vz + 2 * g * height))) / g
        x = vx * t
        y = vy * t
        return x, y, t


__all__ = ["Physics"]
