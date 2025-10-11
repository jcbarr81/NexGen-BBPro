from __future__ import annotations

from dataclasses import dataclass

from .playbalance_config import PlayBalanceConfig


@dataclass
class WarmupTracker:
    """Track warmup state for a bullpen pitcher.

    The tracker counts warmup pitches and keeps track of elapsed time since the
    last thrown pitch.  Timing behaviour is driven by values in
    ``PlayBalanceConfig`` which mirror the constants from the original
    ``PB.INI`` file.
    """

    config: PlayBalanceConfig
    pitches: int = 0
    elapsed: int = 0
    _since_last_pitch: int = 0

    # ------------------------------------------------------------------
    # Pitching actions
    # ------------------------------------------------------------------
    def warm_pitch(self, *, quick: bool = False) -> None:
        """Record a warmup pitch.

        ``quick`` selects the faster timing variant used when the game is in a
        hurry.  Both variants reset the cooldown timer.
        """

        key = "warmupSecsPerQuickPitch" if quick else "warmupSecsPerWarmPitch"
        secs = self.config.get(key, 0)
        self.pitches += 1
        self.elapsed += secs
        self._since_last_pitch = 0

    def maintain_pitch(self) -> None:
        """Record a maintenance pitch to keep the arm warm."""

        secs = self.config.get("warmupSecsPerMaintPitch", 0)
        self.elapsed += secs
        self._since_last_pitch = 0

    # ------------------------------------------------------------------
    # Time progression
    # ------------------------------------------------------------------
    def advance(self, seconds: int) -> None:
        """Advance the internal clock by ``seconds``.

        Once the configured idle time has passed the pitcher slowly loses warmup
        pitches until he is considered cold again.
        """

        if seconds <= 0:
            return
        self.elapsed += seconds
        self._since_last_pitch += seconds
        before_cool = self.config.get("warmupSecsBeforeCool", 0)
        if self._since_last_pitch <= before_cool:
            return
        excess = self._since_last_pitch - before_cool
        cool_secs = self.config.get("warmupSecsPerCoolPitch", 1)
        lost = excess // cool_secs
        if lost:
            self.pitches = max(0, self.pitches - int(lost))
            excess -= lost * cool_secs
            self._since_last_pitch = before_cool + excess
        # Prevent runaway timers when completely cold
        if self.pitches == 0 and self._since_last_pitch > before_cool:
            self._since_last_pitch = before_cool

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def is_ready(self) -> bool:
        """Return ``True`` if the pitcher has thrown enough warmup pitches."""

        needed = self.config.get("warmupPitchCount", 0)
        return self.pitches >= needed
