from datetime import datetime
from pathlib import Path

from utils.path_utils import get_base_dir

NEWS_FILE = get_base_dir() / "data" / "news_feed.txt"


def log_news_event(event: str, file_path: Path = NEWS_FILE):
    """Append a timestamped news event to the news feed file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode="a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {event}\n")
