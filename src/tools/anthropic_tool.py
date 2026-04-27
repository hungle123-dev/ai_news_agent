"""Anthropic news tool for CrewAI."""

from __future__ import annotations

import json

from crewai.tools import BaseTool

from src.sources.anthropic import fetch as anthropic_fetch
from src.config_loader import get_source_config


class AnthropicNewsTool(BaseTool):
    """Fetch Anthropic news from RSS feeds."""

    name: str = "Anthropic News"
    description: str = "Fetch latest Anthropic news, engineering posts, Claude Code changelog, courses and events."

    def _run(self, limit: int = 10) -> str:
        cfg = get_source_config("anthropic")
        cfg["max_items"] = min(limit, 20)
        items = anthropic_fetch(cfg)

        result = []
        for item in items[:limit]:
            result.append(
                {
                    "type": "article",
                    "source": item.source,
                    "title": item.title,
                    "url": item.url,
                    "published": item.published,
                    "summary": item.summary,
                }
            )

        return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    tool = AnthropicNewsTool()
    print(tool.run(5))
