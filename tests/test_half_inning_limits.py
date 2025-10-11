import pytest
from models.player import Player
from models.pitcher import Pitcher
from playbalance.simulation import GameSimulation, TeamState
from tests.util.pbini_factory import make_cfg


def make_player(pid: str) -> Player:
    return Player(
        player_id=pid,
        first_name="F" + pid,
        last_name="L" + pid,
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="1B",
        other_positions=[],
        gf=50,
        ch=50,
        ph=50,
        sp=50,
        pl=0,
        vl=0,
        sc=0,
        fa=0,
        arm=0,
    )


def make_pitcher(pid: str) -> Pitcher:
    return Pitcher(
        player_id=pid,
        first_name="PF" + pid,
        last_name="PL" + pid,
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=50,
        endurance=100,
        control=50,
        movement=50,
        hold_runner=50,
        fb=50,
        cu=0,
        cb=0,
        sl=0,
        si=0,
        scb=0,
        kn=0,
        arm=50,
        fa=50,
        role="SP",
    )


def _basic_sim(cfg):
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    return GameSimulation(home, away, cfg)


def test_half_inning_aborts_after_pa_limit(monkeypatch):
    cfg = make_cfg(maxHalfInningPA=2, maxHalfInningRuns=100, halfInningLimitEnabled=1)
    sim = _basic_sim(cfg)
    monkeypatch.setattr(sim.subs, "maybe_defensive_sub", lambda *a, **k: None)
    monkeypatch.setattr(GameSimulation, "_set_defensive_alignment", lambda *a, **k: None)
    call_count = 0

    def fake_play_at_bat(self, offense, defense):
        nonlocal call_count
        call_count += 1
        if call_count > 5:
            raise RuntimeError("loop")
        offense.runs += 1
        offense.batting_index += 1
        return 0

    monkeypatch.setattr(GameSimulation, "play_at_bat", fake_play_at_bat)
    sim._play_half(sim.home, sim.away)
    assert call_count == 2
    assert sim.home.inning_runs == [2]
    assert any("plate appearances" in m for m in sim.debug_log)


def test_half_inning_aborts_after_run_limit(monkeypatch):
    cfg = make_cfg(maxHalfInningPA=100, maxHalfInningRuns=3, halfInningLimitEnabled=1)
    sim = _basic_sim(cfg)
    monkeypatch.setattr(sim.subs, "maybe_defensive_sub", lambda *a, **k: None)
    monkeypatch.setattr(GameSimulation, "_set_defensive_alignment", lambda *a, **k: None)
    call_count = 0

    def fake_play_at_bat(self, offense, defense):
        nonlocal call_count
        call_count += 1
        if call_count > 5:
            raise RuntimeError("loop")
        offense.runs += 2
        offense.batting_index += 1
        return 0

    monkeypatch.setattr(GameSimulation, "play_at_bat", fake_play_at_bat)
    sim._play_half(sim.home, sim.away)
    assert call_count == 2
    assert sim.home.inning_runs == [4]
    assert any("runs" in m for m in sim.debug_log)


def test_half_inning_limits_can_be_disabled(monkeypatch):
    cfg = make_cfg(maxHalfInningPA=2, maxHalfInningRuns=3, halfInningLimitEnabled=0)
    sim = _basic_sim(cfg)
    monkeypatch.setattr(sim.subs, "maybe_defensive_sub", lambda *a, **k: None)
    monkeypatch.setattr(GameSimulation, "_set_defensive_alignment", lambda *a, **k: None)
    call_count = 0

    def fake_play_at_bat(self, offense, defense):
        nonlocal call_count
        call_count += 1
        if call_count > 5:
            raise RuntimeError("loop")
        offense.runs += 1
        offense.batting_index += 1
        return 0

    monkeypatch.setattr(GameSimulation, "play_at_bat", fake_play_at_bat)
    with pytest.raises(RuntimeError):
        sim._play_half(sim.home, sim.away)
    assert call_count == 6
