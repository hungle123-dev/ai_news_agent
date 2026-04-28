"""
sources/youtube.py — scrape trang /channel/{id}/videos.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

import requests

from src.sources.base import Item

logger = logging.getLogger(__name__)

DEFAULTS = [
    {"name": "Fireship",           "id": "UCsBjURrPoezykLs9EqgamOA"},
    {"name": "AI Explained",       "id": "UCNJ1Ymd5yFuUPtn21xtRbbw"},
    {"name": "Matt Wolfe",         "id": "UChpleBmo18P08aKCIgti38g"},
    {"name": "Matthew Berman",     "id": "UCawZsQWqfGSbCI5yjkdVkTA"},
    {"name": "Two Minute Papers",  "id": "UCbfYPyITQ-7l4upoX8nvctg"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

YT_INIT_RE = re.compile(r"ytInitialData\s*=\s*({.*?});\s*</script>", re.DOTALL)
RELATIVE_RE = re.compile(
    r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago",
    re.IGNORECASE,
)

UNIT_TO_TIMEDELTA = {
    "second": lambda n: timedelta(seconds=n),
    "minute": lambda n: timedelta(minutes=n),
    "hour":   lambda n: timedelta(hours=n),
    "day":    lambda n: timedelta(days=n),
    "week":   lambda n: timedelta(weeks=n),
    "month":  lambda n: timedelta(days=30 * n),
    "year":   lambda n: timedelta(days=365 * n),
}


def _parse_relative(text: str) -> datetime | None:
    if not text:
        return None
    m = RELATIVE_RE.search(text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    delta = UNIT_TO_TIMEDELTA[unit](n)
    return datetime.now(timezone.utc) - delta


def _walk_video_renderers(node, out: list[dict]) -> None:
    if isinstance(node, dict):
        if "videoId" in node and "title" in node:
            out.append(node)
            return
        for v in node.values():
            _walk_video_renderers(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_video_renderers(v, out)


def _extract_videos(html: str) -> list[dict]:
    m = YT_INIT_RE.search(html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    renderers: list[dict] = []
    _walk_video_renderers(data, renderers)
    return renderers


def _fetch_channel(name: str, channel_id: str, limit_per_channel: int) -> list[Item]:
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    tag = f"YouTube/{name}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"{tag}: Lỗi kết nối - {e}")
        return []

    renderers = _extract_videos(resp.text)
    items: list[Item] = []
    seen: set[str] = set()
    for v in renderers:
        vid = v.get("videoId")
        if not vid or vid in seen:
            continue
        seen.add(vid)

        title_obj = v.get("title") or {}
        if isinstance(title_obj, dict):
            runs = title_obj.get("runs") or []
            title = runs[0].get("text") if runs else title_obj.get("simpleText", "")
        else:
            title = str(title_obj)
        if not title:
            continue

        pub_text = ""
        pt = v.get("publishedTimeText") or {}
        if isinstance(pt, dict):
            pub_text = pt.get("simpleText", "")
        pub_dt = _parse_relative(pub_text)
        published = pub_dt.isoformat() if pub_dt else ""

        desc_obj = v.get("descriptionSnippet") or {}
        summary = ""
        if isinstance(desc_obj, dict):
            runs = desc_obj.get("runs") or []
            summary = "".join(r.get("text", "") for r in runs)

        items.append(Item(
            source="YouTube AI",
            title=f"[{name}] {title}",
            url=f"https://www.youtube.com/watch?v={vid}",
            published=published,
            summary=summary[:200] if summary else "No description",
        ))
        if len(items) >= limit_per_channel:
            break

    logger.info(f"{tag}: Lấy thành công {len(items)} videos")
    return items


def fetch(cfg: dict) -> list[Item]:
    channels = cfg.get("channels") or DEFAULTS
    limit = cfg.get("max_items", 2)
    items: list[Item] = []
    for ch in channels:
        items.extend(_fetch_channel(ch["name"], ch["id"], limit))
    return items
