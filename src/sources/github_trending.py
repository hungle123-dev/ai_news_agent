"""GitHub Trending with keyword filter."""

from __future__ import annotations

from src.sources import Item, fetch_feed, filter_by_keywords

BASE_URL = "https://mshibanami.github.io/GitHubTrendingRSS/daily"


def fetch(cfg: dict) -> list[Item]:
    """Fetch GitHub trending with language and keyword filters."""
    languages = cfg.get("languages") or ["python", "typescript"]
    keywords = cfg.get("keywords", [])
    max_items = cfg.get("max_items", 10)
    items: list[Item] = []

    for lang in languages:
        url = f"{BASE_URL}/{lang}.xml"
        items.extend(fetch_feed("GitHub Trending", lang, url, max_items))

    return filter_by_keywords(items, keywords)
