from playbalance.simulation import GameSimulation, TeamState
from tests.test_simulation import MockRandom, make_player, make_pitcher
from tests.util.pbini_factory import make_cfg


def test_step_out_converts_hit_pitch_to_ball():
    cfg = make_cfg(hbpBatterStepOutChance=100)
    batter = make_player("bat")
    home = TeamState(
        lineup=[make_player("h1")],
        bench=[],
        pitchers=[make_pitcher("hp", control=0)],
    )
    away = TeamState(
        lineup=[batter], bench=[], pitchers=[make_pitcher("ap")]
    )
    rng = MockRandom([0.9, 0.99, 0.0, 0.0])
    sim = GameSimulation(home, away, cfg, rng)
    sim.play_at_bat(away, home)
    stats = away.lineup_stats[batter.player_id]
    pitcher_state = home.pitcher_stats["hp"]
    assert stats.hbp == 0
    assert pitcher_state.hbp == 0
    assert pitcher_state.balls_thrown == 1


def test_hit_by_pitch_recorded_on_failed_step_out():
    cfg = make_cfg(hbpBatterStepOutChance=0)
    batter = make_player("bat")
    home = TeamState(
        lineup=[make_player("h1")],
        bench=[],
        pitchers=[make_pitcher("hp", control=0)],
    )
    away = TeamState(
        lineup=[batter], bench=[], pitchers=[make_pitcher("ap")]
    )
    rng = MockRandom([0.9, 0.99, 0.0, 0.0])
    sim = GameSimulation(home, away, cfg, rng)
    outs = sim.play_at_bat(away, home)
    assert outs == 0
    stats = away.lineup_stats[batter.player_id]
    pitcher_state = home.pitcher_stats["hp"]
    assert stats.hbp == 1
    assert pitcher_state.hbp == 1
    assert pitcher_state.balls_thrown == 0
    assert away.bases[0] is stats
