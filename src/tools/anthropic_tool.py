"""
tools/anthropic_tool.py — CrewAI tool lấy tin tức từ Anthropic RSS feeds.
"""

from __future__ import annotations

import json

from crewai.tools import BaseTool

from src.settings import get_source_config
from src.sources.anthropic import fetch as anthropic_fetch


class AnthropicNewsTool(BaseTool):
    name: str = "Anthropic News"
    description: str = (
        "Lấy tin tức mới nhất từ Anthropic: engineering posts, changelog, "
        "courses, và events. Trả về JSON list các bài viết."
    )

    def _run(self, limit: int = 10) -> str:
        cfg = get_source_config("anthropic")
        cfg["max_items"] = min(limit, 20)
        items = anthropic_fetch(cfg)

        result = [
            {"type": "article", "source": item.source, "title": item.title,
             "url": item.url, "published": item.published, "summary": item.summary}
            for item in items[:limit]
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)
