from playbalance.pitch_calibrator import PitchCalibrationDirective
from playbalance.simulation import GameSimulation, TeamState
from tests.test_simulation import make_player, make_pitcher, MockRandom
from tests.util.pbini_factory import make_cfg


class StubCalibrator:
    def __init__(self, directives):
        self.directives = list(directives)
        self.started = 0
        self.finished = 0
        self.tracked: list[bool] = []

    def start_plate_appearance(self) -> None:
        self.started += 1

    def finish_plate_appearance(self) -> None:
        self.finished += 1

    def track_pitch(self, forced: bool = False) -> None:
        self.tracked.append(forced)

    def directive(self, balls: int, strikes: int):
        if self.directives:
            return self.directives.pop(0)
        return None


def _make_sim():
    cfg = make_cfg()
    cfg.values["pitchCalibrationEnabled"] = 1
    home = TeamState(
        lineup=[make_player("home0")],
        bench=[],
        pitchers=[make_pitcher("hp")],
    )
    away = TeamState(
        lineup=[make_player("away0")],
        bench=[],
        pitchers=[make_pitcher("ap")],
    )
    sim = GameSimulation(home, away, cfg, MockRandom([0.0] * 10))
    return sim, home, away


def test_calibration_waste_issues_walk():
    sim, home, away = _make_sim()
    batter = away.lineup[0]
    directives = [
        PitchCalibrationDirective(kind="waste", reason="test") for _ in range(4)
    ]
    stub = StubCalibrator(directives)
    sim.pitch_calibrator = stub

    outs = sim.play_at_bat(away, home)
    batter_state = away.lineup_stats[batter.player_id]
    pitcher_state = home.current_pitcher_state

    assert outs == 0
    assert batter_state.bb == 1
    assert pitcher_state.walks == 1
    assert any("Calibration waste" in entry for entry in sim.debug_log)
    assert stub.started == 1
    assert stub.finished == 1
    assert stub.tracked == [True, True, True, True]


def test_calibration_foul_counts_as_strike():
    sim, home, away = _make_sim()
    batter = away.lineup[0]
    directives = [PitchCalibrationDirective(kind="foul", reason="test")]
    stub = StubCalibrator(directives)
    sim.pitch_calibrator = stub

    outs = sim.play_at_bat(away, home)
    pitcher_state = home.current_pitcher_state

    assert outs in (0, 1)  # outcome depends on deterministic pitch flow
    assert any("Calibration foul" in entry for entry in sim.debug_log)
    assert stub.started == 1
    assert stub.finished == 1
    assert stub.tracked and stub.tracked[0] is True
    assert pitcher_state.first_pitch_strikes == 1


def test_calibration_finishes_on_intentional_walk():
    cfg = make_cfg(
        pitchAroundChanceBase=200,
        defManPitchAroundToIBBPct=100,
        pitchAroundChanceNoInn=0,
    )
    cfg.values["pitchCalibrationEnabled"] = 1
    home = TeamState(
        lineup=[make_player("home0")],
        bench=[],
        pitchers=[make_pitcher("hp")],
    )
    away = TeamState(
        lineup=[make_player("away0")],
        bench=[],
        pitchers=[make_pitcher("ap")],
    )
    sim = GameSimulation(home, away, cfg, MockRandom([0.0] * 4))
    stub = StubCalibrator([])
    sim.pitch_calibrator = stub

    outs = sim.play_at_bat(away, home)

    assert outs == 0
    assert stub.started == 1
    assert stub.finished == 1
    assert stub.tracked == []
