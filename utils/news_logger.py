import os
from datetime import datetime

NEWS_FILE = "data/news_feed.txt"

def log_news_event(event: str, file_path: str = NEWS_FILE):
    """Appends a timestamped news event to the news feed file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, mode="a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {event}\n")
