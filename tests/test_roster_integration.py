import math

from playbalance.config import load_config
from playbalance.benchmarks import load_benchmarks, league_average
from playbalance.player_loader import load_players
from playbalance.orchestrator import Team, simulate_games


def test_real_player_data_influences_results():
    players = load_players("data/players.csv")
    batters = [p for p in players.values() if not p.is_pitcher]
    batters.sort(key=lambda p: p.ratings.get("discipline", 50.0))
    low_lineup = batters[:9]
    high_lineup = batters[-9:]
    pitchers = [p for p in players.values() if p.is_pitcher][:5]
    team_low = Team(low_lineup, pitchers)
    team_high = Team(high_lineup, pitchers)

    cfg = load_config()
    benchmarks = load_benchmarks()
    benchmarks.update(
        {
            "avg_bb_pct": 0.08,
            "avg_k_pct": 0.22,
            "avg_babip": 0.3,
            "avg_sba_per_pa": 0.02,
            "avg_sb_pct": 0.75,
            "avg_pitches_per_pa": 4.0,
        }
    )
    stats_low = simulate_games(cfg, benchmarks, 200, team_low, team_low, rng_seed=1)
    stats_mixed = simulate_games(cfg, benchmarks, 200, team_high, team_low, rng_seed=1)

    bb_low = stats_low.bb / stats_low.pa
    bb_mixed = stats_mixed.bb / stats_mixed.pa
    k_low = stats_low.k / stats_low.pa
    k_mixed = stats_mixed.k / stats_mixed.pa

    assert bb_mixed > bb_low
    assert k_mixed < k_low

    league_bb = league_average(benchmarks, "bb_pct")
    league_k = league_average(benchmarks, "k_pct")
    assert math.isclose(bb_mixed, league_bb, abs_tol=0.05)
    assert math.isclose(k_mixed, league_k, abs_tol=0.05)
