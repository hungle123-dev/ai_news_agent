"""
tools/security_tool.py — CrewAI tool lấy tin tức bảo mật từ RSS feeds.
"""

from __future__ import annotations

import json

from crewai.tools import BaseTool

from src.settings import get_source_config
from src.sources.security import fetch as security_fetch


class SecurityNewsTool(BaseTool):
    name: str = "Security News"
    description: str = (
        "Lấy tin tức bảo mật mới nhất từ The Hacker News, Bleeping Computer, "
        "Krebs on Security và các nguồn uy tín khác. Trả về JSON list bài viết."
    )

    def _run(self, limit: int = 10) -> str:
        cfg = get_source_config("security")
        cfg["max_items"] = min(limit, 20)
        items = security_fetch(cfg)

        result = [
            {"type": "article", "source": item.source, "title": item.title,
             "url": item.url, "published": item.published, "summary": item.summary}
            for item in items[:limit]
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)
