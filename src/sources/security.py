"""
sources/security.py — Thu thập tin tức bảo mật từ các RSS feed.
"""

from __future__ import annotations

from src.sources.base import Item, fetch_feed, filter_by_keywords

_FEEDS = [
    ("The Hacker News",      "https://feeds.feedburner.com/TheHackersNews"),
    ("Bleeping Computer",    "https://www.bleepingcomputer.com/feed/"),
    ("Krebs on Security",    "https://krebsonsecurity.com/feed/"),
    ("Schneier on Security", "https://www.schneier.com/feed/atom/"),
    ("SecurityWeek",         "https://www.securityweek.com/feed/"),
    ("Google Project Zero",  "https://googleprojectzero.blogspot.com/feeds/posts/default"),
]


def fetch(cfg: dict) -> list[Item]:
    """
    Lấy tin bảo mật từ các RSS feed.

    cfg keys:
        feeds     (list[str]): Chỉ lấy feed theo label. Default: tất cả
        keywords  (list[str]): Lọc theo keyword. Default: [] (lấy tất cả)
        max_items (int):       Số item tối đa mỗi feed. Default: 5
    """
    enabled = cfg.get("feeds") or []
    keywords = cfg.get("keywords", [])
    max_items = cfg.get("max_items", 5)

    items: list[Item] = []
    for label, url in _FEEDS:
        if enabled and label not in enabled:
            continue
        items.extend(fetch_feed("Security", label, url, max_items))

    return filter_by_keywords(items, keywords)
