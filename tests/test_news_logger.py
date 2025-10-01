from __future__ import annotations

from pathlib import Path

def test_log_news_event_with_category_and_team(tmp_path: Path):
    from utils.news_logger import log_news_event
    p = tmp_path / "feed.txt"
    log_news_event("Big win for BOS", category="game_recap", team_id="BOS", file_path=p)
    text = p.read_text(encoding="utf-8").strip()
    # Expect both category and team tags present
    assert "[game_recap]" in text and "[BOS]" in text

def test_log_news_json_jsonl(tmp_path: Path):
    from utils.news_logger import log_news_json
    p = tmp_path / "feed.jsonl"
    log_news_json("Trade completed", category="transaction", team_id="NYY", jsonl_path=p)
    line = p.read_text(encoding="utf-8").strip().splitlines()[0]
    assert '"event": "Trade completed"' in line
    assert '"category": "transaction"' in line
    assert '"team_id": "NYY"' in line

