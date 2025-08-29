from logic.simulation import GameSimulation, BatterState, TeamState
from tests.test_simulation import make_player, make_pitcher
from tests.util.pbini_factory import make_cfg


def setup_sim():
    cfg = make_cfg(generalSlop=0, tagTimeSlop=0, relaySlop=0)
    batter = make_player("b")
    offense = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("op")])
    defense = TeamState(lineup=[make_player("d")], bench=[], pitchers=[make_pitcher("dp")])
    sim = GameSimulation(offense, defense, cfg)
    batter_state = BatterState(batter)
    offense.lineup_stats[batter.player_id] = batter_state
    return sim, offense, defense, batter_state


def test_runner_thrown_out_at_home(monkeypatch):
    sim, offense, defense, batter_state = setup_sim()
    runner = BatterState(make_player("r3"))
    offense.bases[2] = runner

    monkeypatch.setattr(sim.physics, "player_speed", lambda sp: 10)
    monkeypatch.setattr(sim.physics, "reaction_delay", lambda pos, fa: 0)
    monkeypatch.setattr(sim.physics, "throw_time", lambda as_rating, distance, position: 8)

    outs = sim._advance_runners(offense, defense, batter_state, bases=1)

    assert outs == 1
    assert offense.runs == 0
    assert offense.bases[0] is batter_state
    assert offense.bases[2] is None


def test_double_play_records_gidp(monkeypatch):
    sim, offense, defense, batter_state = setup_sim()
    runner = BatterState(make_player("r1"))
    offense.bases[0] = runner

    monkeypatch.setattr(sim.physics, "player_speed", lambda sp: 10)
    monkeypatch.setattr(sim.physics, "reaction_delay", lambda pos, fa: 0)
    times = iter([8, 8])
    monkeypatch.setattr(sim.physics, "throw_time", lambda as_rating, distance, position: next(times))

    outs = sim._advance_runners(offense, defense, batter_state, bases=1)

    assert outs == 2
    assert offense.bases == [None, None, None]
    assert batter_state.gidp == 1


def test_fielders_choice_records_fc(monkeypatch):
    sim, offense, defense, batter_state = setup_sim()
    runner = BatterState(make_player("r1"))
    offense.bases[0] = runner

    monkeypatch.setattr(sim.physics, "player_speed", lambda sp: 10)
    monkeypatch.setattr(sim.physics, "reaction_delay", lambda pos, fa: 0)
    times = iter([8, 10])
    monkeypatch.setattr(sim.physics, "throw_time", lambda as_rating, distance, position: next(times))

    outs = sim._advance_runners(offense, defense, batter_state, bases=1)

    assert outs == 1
    assert offense.bases[0] is batter_state
    assert offense.bases[1] is None
    assert batter_state.fc == 1
