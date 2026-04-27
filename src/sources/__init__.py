"""Sources base + utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.utils import setup_logging

logger = setup_logging("ai-news")

USER_AGENT = "Mozilla/5.0 (ai-news/1.0)"
HTTP_TIMEOUT = 20
MAX_ITEMS_PER_FEED = 20


def http_get(url: str) -> str:
    """Fetch URL content."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_published(s: str) -> datetime | None:
    """Parse RSS (RFC 2822) or ISO 8601 date strings."""
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_feed(
    source: str, label: str | None, xml: str, max_items: int = MAX_ITEMS_PER_FEED
) -> list[Item]:
    """Parse RSS 2.0 or Atom feed."""
    soup = BeautifulSoup(xml, "xml")
    entries = soup.find_all("item")
    is_atom = False
    if not entries:
        entries = soup.find_all("entry")
        is_atom = True

    items: list[Item] = []
    for entry in entries[:max_items]:
        title_tag = entry.find("title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        if is_atom:
            link_tag = entry.find("link")
            url = link_tag.get("href", "") if link_tag else ""
            date_tag = entry.find("published") or entry.find("updated")
            desc_tag = entry.find("summary") or entry.find("content")
        else:
            link_tag = entry.find("link")
            url = link_tag.get_text(strip=True) if link_tag else ""
            date_tag = entry.find("pubDate")
            desc_tag = entry.find("description")

        if not url:
            continue
        if label:
            title = f"[{label}] {title}"

        items.append(
            Item(
                source=source,
                title=title,
                url=url.rstrip("/"),
                published=date_tag.get_text(strip=True) if date_tag else "",
                summary=(desc_tag.get_text(strip=True) if desc_tag else "")[:200],
            )
        )
    return items


def fetch_feed(
    source: str, label: str | None, url: str, max_items: int = MAX_ITEMS_PER_FEED
) -> list[Item]:
    """Fetch and parse a feed."""
    tag = source + (f"/{label}" if label else "")
    try:
        xml = http_get(url)
        items = parse_feed(source, label, xml, max_items)
        logger.info(f"  ✓ {tag}: {len(items)} items")
        return items
    except Exception as e:
        logger.warning(f"  ✗ {tag}: {e}")
        return []


def filter_by_keywords(items: list[Item], keywords: list[str]) -> list[Item]:
    """Filter items by keywords."""
    if not keywords:
        return items
    kws = [k.lower() for k in keywords]
    return [
        i
        for i in items
        if any(k in i.title.lower() or k in (i.summary or "").lower() for k in kws)
    ]


@dataclass
class Item:
    source: str
    title: str
    url: str
    published: str = ""
    summary: str = ""

    @property
    def id(self) -> str:
        return self.url
