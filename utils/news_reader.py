def read_latest_news(n=10, file_path="data/news_feed.txt"):
    """Returns the latest N news items as a list of strings (most recent first)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return list(reversed(lines[-n:]))
    except FileNotFoundError:
        return []
