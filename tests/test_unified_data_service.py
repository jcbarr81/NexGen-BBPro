from __future__ import annotations

from pathlib import Path

from services.unified_data_service import get_unified_data_service


def test_players_cache_and_invalidation(tmp_path):
    csv_path = tmp_path / "players.csv"
    csv_path.write_text("dummy\n", encoding="utf-8")

    service = get_unified_data_service()
    service.invalidate_players()  # ensure clean slate

    calls: list[Path] = []

    def loader(resolved: Path):
        calls.append(resolved)
        return [resolved.name]

    first = service.get_players(csv_path, loader)
    second = service.get_players(csv_path, loader)

    assert first == [csv_path.name]
    assert second == [csv_path.name]
    assert len(calls) == 1  # cached after first load

    service.invalidate_players(csv_path)
    service.get_players(csv_path, loader)
    assert len(calls) == 2


def test_roster_cache_and_invalidation(tmp_path):
    service = get_unified_data_service()
    service.invalidate_roster()  # ensure clean slate

    calls: list[tuple[str, Path]] = []

    def loader(team_id: str, resolved_dir: Path):
        calls.append((team_id, resolved_dir))
        return {"team": team_id, "dir": resolved_dir}

    team_id = "AAA"
    roster_dir = tmp_path

    first = service.get_roster(team_id, roster_dir, loader)
    second = service.get_roster(team_id, roster_dir, loader)

    assert first == {"team": team_id, "dir": tmp_path.resolve()}
    assert first is second  # cached object reused
    assert len(calls) == 1

    service.invalidate_roster(team_id=team_id, roster_dir=roster_dir)
    service.get_roster(team_id, roster_dir, loader)
    assert len(calls) == 2
