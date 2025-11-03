from __future__ import annotations

import random
from collections import Counter

from playbalance.orchestrator import _clone_team_state
from playbalance.simulation import GameSimulation, TeamState

from tests.test_simulation import make_player, make_pitcher
from tests.util.pbini_factory import make_cfg


def _make_team(prefix: str) -> TeamState:
    lineup = [make_player(f"{prefix}_b{i}") for i in range(9)]
    bench = [make_player(f"{prefix}_bench{i}") for i in range(3)]
    pitchers = [
        make_pitcher(f"{prefix}_sp", role="SP"),
        make_pitcher(f"{prefix}_rp", role="RP"),
    ]
    return TeamState(lineup=lineup, bench=bench, pitchers=pitchers)


def _simulate_sample(cfg, games: int = 6) -> tuple[Counter, list[float]]:
    base_home = _make_team("home")
    base_away = _make_team("away")
    totals: Counter[str] = Counter()
    directive_rates: list[float] = []
    for idx in range(games):
        home = _clone_team_state(base_home)
        away = _clone_team_state(base_away)
        sim = GameSimulation(home, away, cfg, random.Random(800 + idx))
        sim.simulate_game(persist_stats=False)
        calibrator = getattr(sim, "pitch_calibrator", None)
        if calibrator is not None:
            directive_rates.append(
                calibrator.game_directives / max(1, calibrator.game_plate_appearances)
            )
        for team in (home, away):
            for batter in team.lineup_stats.values():
                totals["pa"] += batter.pa
            for pitcher in team.pitcher_stats.values():
                totals["pitches"] += pitcher.pitches_thrown
    return totals, directive_rates


def test_calibration_disabled_produces_zero_directives():
    cfg = make_cfg()
    cfg.values.update(
        {
            "pitchCalibrationEnabled": 0,
            "pitchCalibrationTarget": 4.0,
        }
    )

    totals, directive_rates = _simulate_sample(cfg)

    assert directive_rates == []
    assert totals["pa"] > 0
    # Baseline average should remain unchanged across runs
    p_per_pa = totals["pitches"] / totals["pa"]
    assert p_per_pa > 0


def test_calibration_enabled_increases_pitch_volume():
    baseline_cfg = make_cfg()
    baseline_cfg.values.update({"pitchCalibrationEnabled": 0})
    baseline_totals, _ = _simulate_sample(baseline_cfg)
    baseline_p_per_pa = baseline_totals["pitches"] / baseline_totals["pa"]

    tuned_cfg = make_cfg(
        pitchCalibrationEnabled=1,
        pitchCalibrationTarget=6.0,
        pitchCalibrationTolerance=0.0,
        pitchCalibrationPerPlateCap=2,
        pitchCalibrationPerGameCap=0,
        pitchCalibrationMinPA=1,
        pitchCalibrationPreferFoul=1,
        pitchCalibrationEmaAlpha=0.5,
    )
    tuned_totals, directive_rates = _simulate_sample(tuned_cfg)
    tuned_p_per_pa = tuned_totals["pitches"] / tuned_totals["pa"]

    assert directive_rates  # calibration injects corrective pitches
    assert tuned_p_per_pa > baseline_p_per_pa + 0.5


def test_calibration_tracks_real_pitch_totals():
    cfg = make_cfg(
        pitchCalibrationEnabled=1,
        pitchCalibrationTarget=5.5,
        pitchCalibrationTolerance=0.0,
        pitchCalibrationPerPlateCap=2,
        pitchCalibrationPerGameCap=0,
        pitchCalibrationMinPA=1,
        pitchCalibrationPreferFoul=1,
        pitchCalibrationEmaAlpha=0.4,
    )
    home = _make_team("home")
    away = _make_team("away")
    sim = GameSimulation(
        _clone_team_state(home),
        _clone_team_state(away),
        cfg,
        random.Random(900),
    )
    sim.simulate_game(persist_stats=False)
    calibrator = sim.pitch_calibrator
    assert calibrator is not None
    total_pitches = sum(
        state.pitches_thrown
        for team in (sim.home, sim.away)
        for state in team.pitcher_stats.values()
    )
    # Calibrator tracks every pitch it observes; in edge cases (e.g. partial
    # appearances) the tracker may include a corrective pitch that never
    # reached the stat table, but the delta is bounded by the number of
    # directives.
    assert total_pitches <= calibrator.game_pitches
    assert calibrator.game_pitches - total_pitches <= calibrator.game_directives
    assert calibrator.game_directives > 0
