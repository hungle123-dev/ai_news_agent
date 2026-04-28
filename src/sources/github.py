"""
sources/github.py — Thu thập GitHub Trending repos qua RSS feed.

Dùng RSS feed từ: https://mshibanami.github.io/GitHubTrendingRSS/
"""

from __future__ import annotations

from src.sources.base import Item, fetch_feed, filter_by_keywords

_RSS_BASE = "https://mshibanami.github.io/GitHubTrendingRSS/daily"


def fetch(cfg: dict) -> list[Item]:
    """
    Lấy GitHub trending repos theo ngôn ngữ và lọc theo keyword.

    cfg keys:
        languages (list[str]): Ngôn ngữ cần theo dõi. Default: ["python", "typescript"]
        keywords  (list[str]): Chỉ giữ repo match keyword. Default: [] (lấy tất cả)
        max_items (int):       Số repo tối đa mỗi ngôn ngữ. Default: 10
    """
    languages = cfg.get("languages") or ["python", "typescript"]
    keywords = cfg.get("keywords", [])
    max_items = cfg.get("max_items", 10)

    items: list[Item] = []
    for lang in languages:
        url = f"{_RSS_BASE}/{lang}.xml"
        items.extend(fetch_feed("GitHub Trending", lang.capitalize(), url, max_items))

    return filter_by_keywords(items, keywords)
