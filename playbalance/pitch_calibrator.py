from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class PitchCalibrationSettings:
    """Tuning knobs for :class:`PitchCountCalibrator`.

    Attributes
    ----------
    target_pitches_per_pa:
        Desired average pitches per plate appearance.
    ema_alpha:
        Smoothing factor for the exponential moving average. Higher values
        weight the most recent plate appearance more heavily.
    tolerance:
        Minimum shortfall from the target before issuing a directive.
    per_plate_cap:
        Maximum number of corrective pitches per plate appearance. ``0``
        disables per-PA limits.
    per_game_cap:
        Maximum number of corrective pitches for the current game. ``0``
        disables the cap.
    min_plate_appearances:
        Minimum completed plate appearances before the calibrator starts
        issuing directives. Prevents noisy early adjustments.
    prefer_foul_on_two_strikes:
        When ``True`` the calibrator prefers foul directives once the batter
        has two strikes; otherwise waste pitches are suggested.
    """

    target_pitches_per_pa: float = 3.9
    ema_alpha: float = 0.1
    tolerance: float = 0.05
    per_plate_cap: int = 1
    per_game_cap: int = 30
    min_plate_appearances: int = 6
    prefer_foul_on_two_strikes: bool = True
    expected_pa_per_game: int = 76


@dataclass(slots=True)
class PitchCalibrationDirective:
    """Instruction indicating the type of corrective pitch to inject."""

    kind: str  # Expected values: "waste" or "foul"
    reason: str


class PitchCountCalibrator:
    """Tracks in-game pitch counts and recommends corrective pitches.

    The calibrator maintains an exponential moving average (EMA) of pitches
    per plate appearance to smooth short-term variance. When the average
    falls below the configured target by more than the tolerance, the
    calibrator issues directives capped per plate appearance and per game.
    """

    def __init__(self, settings: Optional[PitchCalibrationSettings] = None) -> None:
        self.settings = settings or PitchCalibrationSettings()
        self._active_pa = False
        self._ema = self.settings.target_pitches_per_pa
        self._game_pitches = 0
        self._game_plate_appearances = 0
        self._game_directives = 0
        self._current_pa_pitches = 0
        self._current_pa_directives = 0
        self._fractional_deficit = 0.0

    # ------------------------------------------------------------------
    # Plate appearance lifecycle
    # ------------------------------------------------------------------
    def start_plate_appearance(self) -> None:
        """Begin tracking a new plate appearance."""

        if self._active_pa:
            raise RuntimeError("Plate appearance already active")
        self._active_pa = True
        self._current_pa_pitches = 0
        self._current_pa_directives = 0

    def track_pitch(self, *, forced: bool = False) -> None:
        """Record a pitch thrown during the active plate appearance.

        Parameters
        ----------
        forced:
            ``True`` when the pitch was injected by the calibrator. Forced
            pitches count toward the per-PA and per-game directive caps.
        """

        if not self._active_pa:
            return
        self._current_pa_pitches += 1
        self._game_pitches += 1
        if forced:
            self._current_pa_directives += 1
            self._game_directives += 1

    def finish_plate_appearance(self) -> None:
        """Finalize the active plate appearance and update the EMA."""

        if not self._active_pa:
            return

        self._game_plate_appearances += 1
        observed = self._current_pa_pitches
        if self._game_plate_appearances == 1:
            self._ema = observed
        else:
            alpha = self.settings.ema_alpha
            self._ema = (alpha * observed) + ((1.0 - alpha) * self._ema)

        self._active_pa = False
        self._current_pa_pitches = 0
        self._current_pa_directives = 0

    # ------------------------------------------------------------------
    # Directive logic
    # ------------------------------------------------------------------
    def directive(self, balls: int, strikes: int) -> Optional[PitchCalibrationDirective]:
        """Return a corrective pitch directive when needed.

        The calibrator only issues a directive when:
          * A plate appearance is active.
          * Per-PA and per-game caps allow additional pitches.
          * The EMA sits below the target by more than the tolerance.
          * The minimum sample threshold has been met.
        """

        if not self._active_pa:
            return None

        per_plate_cap = self.settings.per_plate_cap
        if per_plate_cap > 0 and self._current_pa_directives >= per_plate_cap:
            return None

        per_game_cap = self.settings.per_game_cap
        if per_game_cap > 0 and self._game_directives >= per_game_cap:
            return None

        if self._game_plate_appearances < self.settings.min_plate_appearances:
            return None

        needed_total = self._remaining_needed()
        if needed_total <= self.settings.tolerance:
            return None

        remaining_pas = max(self._remaining_plate_appearances(), 1)
        per_pa_need = needed_total / remaining_pas
        if per_pa_need <= self.settings.tolerance:
            return None

        self._fractional_deficit += per_pa_need
        if self._fractional_deficit < 1.0:
            return None
        self._fractional_deficit -= 1.0

        kind = "waste"
        if strikes >= 2 and self.settings.prefer_foul_on_two_strikes:
            kind = "foul"

        return PitchCalibrationDirective(
            kind=kind,
            reason="raise_average",
        )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    @property
    def ema(self) -> float:
        """Current exponential moving average of pitches per plate appearance."""

        return self._ema

    @property
    def game_pitches(self) -> int:
        """Total pitches tracked for the current game."""

        return self._game_pitches

    @property
    def game_plate_appearances(self) -> int:
        """Total plate appearances completed in the current game."""

        return self._game_plate_appearances

    @property
    def game_directives(self) -> int:
        """Number of corrective pitches issued in the current game."""

        return self._game_directives

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remaining_needed(self) -> float:
        completed_expected = (
            self.settings.target_pitches_per_pa * self._game_plate_appearances
        )
        completed_actual = self._game_pitches - self._current_pa_pitches
        deficit = completed_expected - completed_actual

        if deficit > 0 and self._current_pa_pitches > 0:
            current_deficit = (
                self.settings.target_pitches_per_pa - self._current_pa_pitches
            )
            deficit = max(deficit, current_deficit)

        return max(deficit, 0.0)

    def _remaining_plate_appearances(self) -> int:
        expected = max(self.settings.expected_pa_per_game, 1)
        completed = self._game_plate_appearances
        if self._active_pa:
            completed += 1
        return max(expected - completed, 1)
