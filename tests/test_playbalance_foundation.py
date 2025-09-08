"""Basic tests for the playbalance scaffolding."""
from playbalance import load_config, load_benchmarks


def test_load_config_sections():
    cfg = load_config()
    # The PBINI file is a single "PlayBalance" section with many entries.
    assert "PlayBalance" in cfg.sections
    assert cfg.get("PlayBalance", "speedBase") is not None


def test_load_benchmarks_has_values():
    benchmarks = load_benchmarks()
    assert benchmarks["pitches_put_in_play_pct"] == 0.175
