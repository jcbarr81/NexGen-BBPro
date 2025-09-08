"""Basic tests for the playbalance scaffolding."""
from playbalance import (
    load_config,
    load_benchmarks,
    park_factors,
    weather_profile,
    league_averages,
)


def test_load_config_sections():
    cfg = load_config()
    # The PBINI file is a single "PlayBalance" section with many entries.
    assert "PlayBalance" in cfg.sections
    assert cfg.get("PlayBalance", "speedBase") is not None
    # Attribute access exposes the same value.
    assert cfg.speedBase == cfg.sections["PlayBalance"].speedBase


def test_load_benchmarks_has_values():
    benchmarks = load_benchmarks()
    assert benchmarks["pitches_put_in_play_pct"] == 0.175
    # Helper slices of the benchmark data
    pf = park_factors(benchmarks)
    assert pf["overall"] == 100.0
    weather = weather_profile(benchmarks)
    assert weather["temperature"] == 75.0
    avgs = league_averages(benchmarks)
    assert avgs["exit_velocity"] == 88.5
