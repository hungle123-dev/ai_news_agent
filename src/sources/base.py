"""
sources/base.py — Base classes và helpers dùng chung cho tất cả sources.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


@dataclass
class Item:
    """Một mục tin tức thu thập được từ bất kỳ nguồn nào."""
    source: str      # Tên nguồn, e.g. "Anthropic", "GitHub Trending"
    title: str
    url: str
    published: str = ""   # ISO 8601 hoặc chuỗi ngày
    summary: str = ""


# ── HTTP ───────────────────────────────────────────────────────────────────────

_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = "Mozilla/5.0 (AI-News-Agent/1.0)"
    return _SESSION


def http_get(url: str, timeout: int = 15) -> requests.Response | None:
    """GET request, trả về None nếu lỗi."""
    try:
        resp = _get_session().get(url, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as e:
        logger.warning("HTTP GET failed: %s — %s", url, e)
        return None


# ── RSS Feed Parsing ───────────────────────────────────────────────────────────

def fetch_feed(source_name: str, feed_label: str, url: str, max_items: int = 50) -> list[Item]:
    """
    Parse một RSS/Atom feed và trả về list[Item].

    Args:
        source_name: Tên nhóm nguồn, e.g. "Anthropic"
        feed_label:  Tên feed cụ thể, e.g. "Engineering Blog"
        url:         URL của feed
        max_items:   Số lượng tối đa item cần lấy
    """
    resp = http_get(url)
    if resp is None:
        return []

    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.warning("XML parse error for %s: %s", url, e)
        return []

    # Support both RSS <item> và Atom <entry>
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall(".//item") or root.findall(".//atom:entry", ns)

    items: list[Item] = []
    for entry in entries[:max_items]:
        title = _text(entry, ["title", "atom:title"], ns) or "(no title)"
        link = _get_link(entry, ns)
        pub = _parse_date(_text(entry, ["pubDate", "published", "updated", "atom:published", "atom:updated"], ns))
        desc = _strip_html(_text(entry, ["description", "summary", "atom:summary", "content", "atom:content"], ns) or "")

        if link:
            items.append(Item(
                source=f"{source_name} — {feed_label}" if feed_label else source_name,
                title=title.strip(),
                url=link,
                published=pub,
                summary=desc[:500],
            ))

    return items


def _text(elem, tags: list[str], ns: dict) -> str | None:
    for tag in tags:
        child = elem.find(tag, ns)
        if child is not None and child.text:
            return child.text.strip()
    return None


def _get_link(entry, ns: dict) -> str | None:
    # Atom: <link href="..."/>
    link_el = entry.find("atom:link", ns) or entry.find("link")
    if link_el is not None:
        href = link_el.get("href") or (link_el.text or "").strip()
        if href:
            return href
    return None


def _parse_date(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).isoformat()
    except Exception:
        return raw


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


# ── Keyword Filter ─────────────────────────────────────────────────────────────

def filter_by_keywords(items: list[Item], keywords: list[str]) -> list[Item]:
    """
    Giữ lại các item có ít nhất một keyword trong title hoặc summary.
    Nếu keywords rỗng → trả về tất cả.
    """
    if not keywords:
        return items

    kws = [k.lower() for k in keywords]

    def matches(item: Item) -> bool:
        text = (item.title + " " + item.summary).lower()
        return any(k in text for k in kws)

    return [item for item in items if matches(item)]
