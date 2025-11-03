from playbalance.pitch_calibrator import (
    PitchCalibrationDirective,
    PitchCalibrationSettings,
    PitchCountCalibrator,
)


def make_calibrator(**overrides):
    settings = PitchCalibrationSettings(**overrides)
    return PitchCountCalibrator(settings)


def complete_plate(calibrator: PitchCountCalibrator, pitches: int, *, forced: int = 0) -> None:
    calibrator.start_plate_appearance()
    for _ in range(forced):
        calibrator.track_pitch(forced=True)
    for _ in range(pitches - forced):
        calibrator.track_pitch()
    calibrator.finish_plate_appearance()


def test_ema_updates_with_plate_appearances():
    calibrator = make_calibrator(
        target_pitches_per_pa=4.0,
        ema_alpha=0.5,
        tolerance=0.0,
        min_plate_appearances=0,
    )

    complete_plate(calibrator, pitches=3)
    assert calibrator.ema == 3

    complete_plate(calibrator, pitches=5)
    assert calibrator.ema == 4  # 0.5 * 5 + 0.5 * 3


def test_directive_respects_per_plate_cap():
    calibrator = make_calibrator(
        target_pitches_per_pa=4.0,
        ema_alpha=1.0,
        tolerance=0.0,
        per_plate_cap=1,
        per_game_cap=10,
        min_plate_appearances=0,
        expected_pa_per_game=1,
    )

    complete_plate(calibrator, pitches=2)

    calibrator.start_plate_appearance()
    directive = calibrator.directive(balls=0, strikes=0)
    assert isinstance(directive, PitchCalibrationDirective)

    calibrator.track_pitch(forced=True)
    second = calibrator.directive(balls=0, strikes=0)
    assert second is None


def test_directive_respects_per_game_cap():
    calibrator = make_calibrator(
        target_pitches_per_pa=4.0,
        ema_alpha=1.0,
        tolerance=0.0,
        per_plate_cap=5,
        per_game_cap=2,
        min_plate_appearances=0,
        expected_pa_per_game=1,
    )

    complete_plate(calibrator, pitches=2)

    calibrator.start_plate_appearance()
    first = calibrator.directive(balls=0, strikes=0)
    assert isinstance(first, PitchCalibrationDirective)
    calibrator.track_pitch(forced=True)
    calibrator.finish_plate_appearance()

    calibrator.start_plate_appearance()
    second = calibrator.directive(balls=0, strikes=0)
    assert isinstance(second, PitchCalibrationDirective)
    calibrator.track_pitch(forced=True)

    third = calibrator.directive(balls=0, strikes=0)
    assert third is None


def test_directive_none_when_target_satisfied():
    calibrator = make_calibrator(
        target_pitches_per_pa=4.0,
        ema_alpha=1.0,
        tolerance=0.1,
        per_plate_cap=1,
        per_game_cap=5,
        min_plate_appearances=0,
    )

    complete_plate(calibrator, pitches=4)

    calibrator.start_plate_appearance()
    directive = calibrator.directive(balls=0, strikes=2)
    assert directive is None
