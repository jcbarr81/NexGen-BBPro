from pathlib import Path

from utils.path_utils import get_base_dir


def read_latest_news(n: int = 10, file_path: str | Path = "data/news_feed.txt"):
    """Return the latest ``n`` news items (most recent first)."""

    path = Path(file_path)
    if not path.is_absolute():
        path = get_base_dir() / path
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        return list(reversed(lines[-n:]))
    except FileNotFoundError:
        return []
