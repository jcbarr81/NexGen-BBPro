from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .playbalance_config import PlayBalanceConfig


@dataclass
class FieldingAI:
    """Decision helpers for defensive actions based on timing slop values."""

    config: PlayBalanceConfig
    rng: Random | None = None

    def catch_action(self, hang_time: float, run_time: float) -> str:
        """Return the action to take on a fly ball.

        The returned string is one of ``"catch"`` for an easy catch,
        ``"dive"`` when the fielder should make an effort, or
        ``"no_attempt"`` if the ball cannot be reached in time.
        """

        t = run_time + self.config.generalSlop
        if t + self.config.shouldBeCaughtSlop <= hang_time:
            return "catch"
        if t + self.config.couldBeCaughtSlop <= hang_time:
            return "dive"
        return "no_attempt"

    def catch_probability(
        self, position: str, fa: int, hang_time: float, action: str
    ) -> float:
        """Return the probability of successfully catching the ball.

        ``position`` is the fielder's defensive position and ``fa`` their
        fielding ability rating. ``hang_time`` represents either the time a
        fly ball spends in the air or the time a throw takes to reach the
        fielder. ``action`` is one of ``"catch"``, ``"dive"`` or ``"leap"``.

        The calculation is influenced by several ``PlayBalance`` configuration
        values. A 100% probability is returned when ``hang_time`` exceeds the
        ``automaticCatchDist`` threshold.
        """

        if hang_time >= self.config.automaticCatchDist:
            return 1.0

        chance = self.config.catchBaseChance + fa / self.config.catchFADiv

        if hang_time < 1.0:
            chance += self.config.catchChanceLessThan1Sec
            tenths = int((1.0 - hang_time) * 10)
            chance += tenths * self.config.catchChancePerTenth

        if action == "dive":
            chance += self.config.catchChanceDiving
        elif action == "leap":
            chance += self.config.catchChanceLeaping

        pos_adjust = {
            "P": self.config.catchChancePitcherAdjust,
            "C": self.config.catchChanceCatcherAdjust,
            "1B": self.config.catchChanceFirstBaseAdjust,
            "2B": self.config.catchChanceSecondBaseAdjust,
            "3B": self.config.catchChanceThirdBaseAdjust,
            "SS": self.config.catchChanceShortStopAdjust,
            "LF": self.config.catchChanceLeftFieldAdjust,
            "CF": self.config.catchChanceCenterFieldAdjust,
            "RF": self.config.catchChanceRightFieldAdjust,
        }
        chance += pos_adjust.get(position, 0)

        return max(0.0, min(1.0, chance / 100))

    def resolve_fly_ball(
        self, position: str, fa: int, hang_time: float, action: str
    ) -> bool:
        """Return ``True`` if the fly ball is caught."""

        prob = self.catch_probability(position, fa, hang_time, action)
        rng = self.rng or Random()
        return rng.random() < prob

    def resolve_throw(
        self, position: str, fa: int, hang_time: float, action: str = "catch"
    ) -> bool:
        """Return ``True`` if the thrown ball is caught."""

        prob = self.catch_probability(position, fa, hang_time, action)
        rng = self.rng or Random()
        return rng.random() < prob

    def should_relay_throw(self, fielder_time: float, runner_time: float) -> bool:
        """Return ``True`` if a relay throw should be attempted."""

        return (
            fielder_time + self.config.generalSlop + self.config.relaySlop
            <= runner_time
        )

    def should_tag_runner(self, fielder_time: float, runner_time: float) -> bool:
        """Return ``True`` if a tag play beats the runner."""

        return (
            fielder_time + self.config.generalSlop + self.config.tagTimeSlop
            <= runner_time
        )

    def should_run_to_bag(self, fielder_time: float, runner_time: float) -> bool:
        """Return ``True`` if the fielder can reach the bag in time."""

        return (
            fielder_time + self.config.generalSlop + self.config.stepOnBagSlop
            <= runner_time
        )
