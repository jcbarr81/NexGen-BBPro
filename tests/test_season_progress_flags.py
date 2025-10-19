import json

from services import season_progress_flags as spf


def test_mark_draft_completed_creates_file(tmp_path, monkeypatch):
    target = tmp_path / "progress.json"
    monkeypatch.setattr(spf, "PROGRESS_PATH", target)

    spf.mark_draft_completed(2025, retries=2, delay=0)

    payload = json.loads(target.read_text())
    assert payload["draft_completed_years"] == [2025]


def test_mark_draft_completed_retries_on_replace_error(tmp_path, monkeypatch):
    target = tmp_path / "progress.json"
    monkeypatch.setattr(spf, "PROGRESS_PATH", target)

    original_replace = spf.os.replace
    call_count = {"count": 0}

    def flaky_replace(src, dst):  # pragma: no cover - deterministic in test
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise PermissionError("busy")
        return original_replace(src, dst)

    monkeypatch.setattr(spf.os, "replace", flaky_replace)

    spf.mark_draft_completed(2030, retries=3, delay=0)

    payload = json.loads(target.read_text())
    assert payload["draft_completed_years"] == [2030]
    assert call_count["count"] >= 2


def test_mark_playoffs_completed_sets_flag(tmp_path):
    target = tmp_path / "progress.json"
    target.write_text(json.dumps({"draft_completed_years": [2024]}))

    spf.mark_playoffs_completed(progress_path=target, retries=2, delay=0)

    payload = json.loads(target.read_text())
    assert payload["playoffs_done"] is True
    assert payload["draft_completed_years"] == [2024]


def test_mark_playoffs_completed_idempotent(tmp_path):
    target = tmp_path / "progress.json"
    target.write_text(json.dumps({"playoffs_done": True}))

    spf.mark_playoffs_completed(progress_path=target, retries=2, delay=0)

    payload = json.loads(target.read_text())
    assert payload["playoffs_done"] is True
