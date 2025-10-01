from datetime import datetime
from pathlib import Path
import json

from utils.path_utils import get_base_dir

NEWS_FILE = get_base_dir() / "data" / "news_feed.txt"
NEWS_JSONL = get_base_dir() / "data" / "news_feed.jsonl"


def log_news_event(event: str, *, category: str | None = None, team_id: str | None = None, file_path: Path = NEWS_FILE):
    """Append a timestamped news event to the news feed file.

    Parameters
    ----------
    event:
        Human-readable message.
    category:
        Optional category tag (e.g., "game_recap", "injury", "transaction").
    team_id:
        Optional team identifier for filtering in UIs.
    file_path:
        Destination text file; defaults to ``data/news_feed.txt``.
    """

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tag_cat = f" [{category}]" if category else ""
    tag_team = f" [{team_id}]" if team_id else ""
    with path.open(mode="a", encoding="utf-8") as f:
        f.write(f"[{timestamp}]{tag_cat}{tag_team} {event}\n")


def log_news_json(event: str, *, category: str | None = None, team_id: str | None = None, jsonl_path: Path = NEWS_JSONL) -> None:
    """Append a structured news event as JSONL for programmatic consumption."""

    rec = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "category": category,
        "team_id": team_id,
    }
    path = Path(jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
