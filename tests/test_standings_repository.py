from __future__ import annotations

import json
from pathlib import Path

from services.standings_repository import (
    invalidate_standings,
    load_standings,
    save_standings,
)


def test_load_standings_uses_cache_until_invalidated(tmp_path):
    standings_file = tmp_path / "standings.json"
    standings_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"AAA": {"wins": 10, "losses": 5, "last10": ["W", "w", "L"]}}
    standings_file.write_text(json.dumps(payload), encoding="utf-8")

    invalidate_standings(base_path=standings_file)
    first = load_standings(base_path=standings_file)
    assert first["AAA"]["wins"] == 10
    assert first["AAA"]["last10"] == ["W", "W", "L"]

    standings_file.write_text(json.dumps({"AAA": {"wins": 20, "losses": 1}}), encoding="utf-8")
    second = load_standings(base_path=standings_file)
    assert second["AAA"]["wins"] == 10  # cached value

    invalidate_standings(base_path=standings_file)
    third = load_standings(base_path=standings_file)
    assert third["AAA"]["wins"] == 20


def test_save_standings_persists_and_updates_cache(tmp_path):
    data_dir = tmp_path / "data"
    invalidate_standings(base_path=data_dir)

    initial = {"AAA": {"wins": 5, "losses": 3}}
    save_standings(initial, base_path=data_dir)

    saved_path = data_dir if data_dir.suffix else data_dir / "standings.json"
    path = Path(saved_path)
    if path.is_dir():
        path = path / "standings.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored == {"AAA": {"wins": 5, "losses": 3}}

    cached = load_standings(base_path=data_dir)
    assert cached["AAA"]["wins"] == 5

    updated = {"AAA": {"wins": 7, "losses": 3}}
    save_standings(updated, base_path=data_dir)
    refreshed = load_standings(base_path=data_dir)
    assert refreshed["AAA"]["wins"] == 7
