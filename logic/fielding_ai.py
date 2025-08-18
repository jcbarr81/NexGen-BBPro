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
