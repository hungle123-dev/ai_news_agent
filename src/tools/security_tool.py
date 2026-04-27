"""Security news tool for CrewAI."""

from __future__ import annotations

import json

from crewai.tools import BaseTool

from src.sources.security import fetch as security_fetch
from src.config_loader import get_source_config


class SecurityNewsTool(BaseTool):
    """Fetch security news from various feeds."""

    name: str = "Security News"
    description: str = "Fetch latest security news from Hacker News, Bleeping Computer, Krebs on Security, and other security feeds."

    def _run(self, limit: int = 10) -> str:
        cfg = get_source_config("security")
        cfg["max_items"] = min(limit, 20)
        items = security_fetch(cfg)

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
    tool = SecurityNewsTool()
    print(tool.run(5))
