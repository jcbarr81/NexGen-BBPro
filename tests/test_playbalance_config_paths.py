from playbalance.config import load_config


def test_load_config_outside_repo(monkeypatch, tmp_path):
    """``load_config`` should locate PBINI.txt relative to the project root."""

    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert "PlayBalance" in cfg.sections
