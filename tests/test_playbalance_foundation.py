"""Basic tests for the playbalance scaffolding."""
import random

from playbalance import Benchmarks, PlayBalanceConfig, load_benchmarks, load_config
from playbalance.probability import roll, weighted_choice
from playbalance.ratings import rating_to_pct
from playbalance.state import GameState, PlayerState, TeamState


def test_load_config_sections(tmp_path):
    override = tmp_path / "override.json"
    override.write_text('{"PlayBalance": {"speedBase": 42}}')

    cfg = load_config(overrides_path=override)
    # The PBINI file uses a single "PlayBalance" section with many entries.
    assert isinstance(cfg, PlayBalanceConfig)
    assert cfg.PlayBalance.speedBase == 42
    assert cfg.get("PlayBalance", "speedBase") == 42


def test_benchmarks_helpers():
    benchmarks = load_benchmarks()
    assert isinstance(benchmarks, Benchmarks)
    assert benchmarks.league_average("babip") == 0.291
    assert benchmarks.park_factors()["overall"] == 100.0
    assert benchmarks.weather_means()["temperature"] == 75.0


def test_probability_and_state():
    random.seed(0)
    assert weighted_choice([0.0, 1.0], items=["a", "b"]) == "b"
    assert roll(1.0) is True

    player = PlayerState("Test", {"contact": 50})
    team = TeamState("A", [player])
    game = GameState(teams={"home": team, "away": team})
    assert game.teams["home"].lineup[0].name == "Test"
    assert rating_to_pct(50) == 0.5
