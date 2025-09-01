import contextlib
import io
from datetime import timedelta

import scripts.simulate_season_avg as ssa
import logic.simulation as sim
from tests.test_physics import make_player, make_pitcher
from logic.simulation import TeamState


def _run_sim(monkeypatch):
    monkeypatch.setattr(sim, "save_stats", lambda players, teams: None)

    def short_schedule(teams, start_date):
        return [
            {"date": (start_date + timedelta(days=i)).isoformat(), "home": teams[0], "away": teams[1]}
            for i in range(10)
        ]

    class DummyTeam:
        def __init__(self, tid):
            self.team_id = tid

    def short_load():
        return [DummyTeam("T1"), DummyTeam("T2")]

    def fake_build(team_id):
        lineup = [make_player(f"{team_id}{i}") for i in range(9)]
        pitchers = [make_pitcher(f"{team_id}p")]
        return TeamState(lineup=lineup, bench=[], pitchers=pitchers)

    monkeypatch.setattr(ssa, "generate_mlb_schedule", short_schedule)
    monkeypatch.setattr(ssa, "load_teams", short_load)
    monkeypatch.setattr(ssa, "build_default_game_state", fake_build)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ssa.simulate_season_average(use_tqdm=False)
    return buf.getvalue().splitlines()


def _parse(lines, prefix):
    for line in lines:
        if line.startswith(prefix):
            return float(line.split(":", 1)[1].strip())
    raise AssertionError(f"{prefix} not found")


def test_simulation_double_play_rate(monkeypatch):
    lines = _run_sim(monkeypatch)
    dp_rate = _parse(lines, "DoublePlayRate")
    assert dp_rate < 0.03
