"""
sources/anthropic.py — Thu thập tin tức từ Anthropic.

Anthropic không còn cung cấp RSS feeds công khai, nên scrape trực tiếp trang news.
Dùng Beautiful Soup để parse HTML.
"""

from __future__ import annotations

import logging
import re

from src.sources.base import Item, http_get, filter_by_keywords

logger = logging.getLogger(__name__)

_NEWS_URL = "https://www.anthropic.com/news"


def fetch(cfg: dict) -> list[Item]:
    """
    Scrape trang tin tức của Anthropic.

    cfg keys:
        keywords  (list[str]): Lọc theo keyword. Default: [] (lấy tất cả)
        max_items (int):       Số bài tối đa. Default: 20
    """
    keywords = cfg.get("keywords", [])
    max_items = cfg.get("max_items", 20)

    items = _scrape_news(max_items)
    return filter_by_keywords(items, keywords)


def _scrape_news(max_items: int) -> list[Item]:
    """Scrape trang /news của Anthropic."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("BeautifulSoup không được cài. Chạy: pip install beautifulsoup4")
        return []

    resp = http_get(_NEWS_URL)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items: list[Item] = []

    # Tìm các article cards — Anthropic dùng nhiều layout khác nhau
    # Thử các selector phổ biến
    cards = (
        soup.select("a[href*='/news/']") or
        soup.select("article a") or
        soup.select(".PostCard, .news-card, [class*='post'], [class*='card']")
    )

    seen_urls: set[str] = set()
    for el in cards:
        try:
            # Lấy href
            href = el.get("href", "")
            if not href or "/news/" not in href:
                continue
            url = f"https://www.anthropic.com{href}" if href.startswith("/") else href
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Lấy title từ heading trong card hoặc từ text của link
            title_el = el.find(["h1", "h2", "h3", "h4"])
            title = title_el.get_text(strip=True) if title_el else el.get_text(strip=True)
            title = re.sub(r"\s+", " ", title).strip()

            if not title or len(title) < 5:
                continue

            # Lấy description nếu có
            desc_el = el.find("p")
            summary = desc_el.get_text(strip=True) if desc_el else ""

            items.append(Item(
                source="Anthropic",
                title=title,
                url=url,
                summary=summary[:300],
            ))

            if len(items) >= max_items:
                break

        except Exception:
            continue

    logger.info("Anthropic: scraped %d items", len(items))
    return items
