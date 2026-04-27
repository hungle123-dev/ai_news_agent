"""Security feeds - The Hacker News, Bleeping Computer, Krebs on Security, etc."""

from __future__ import annotations

from src.sources import Item, fetch_feed, filter_by_keywords

FEEDS = [
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("Bleeping Computer", "https://www.bleepingcomputer.com/feed/"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ("Schneier on Security", "https://www.schneier.com/feed/atom/"),
    ("SecurityWeek", "https://www.securityweek.com/feed/"),
    (
        "Google Project Zero",
        "https://googleprojectzero.blogspot.com/feeds/posts/default",
    ),
]


def fetch(cfg: dict) -> list[Item]:
    """Fetch security feeds."""
    enabled_feeds = cfg.get("feeds") or []
    keywords = cfg.get("keywords", [])
    items: list[Item] = []

    for label, url in FEEDS:
        if enabled_feeds and label not in enabled_feeds:
            continue
        items.extend(fetch_feed("Security", label, url))

    return filter_by_keywords(items, keywords)
