"""GitHub RSS tool for CrewAI."""

from __future__ import annotations

import json

from crewai.tools import BaseTool

from src.sources.github_trending import fetch as github_fetch
from src.config_loader import get_source_config


class GitHubRSSTool(BaseTool):
    """Fetch GitHub trending repos using RSS."""

    name: str = "GitHub Trending RSS"
    description: str = (
        "Fetch trending GitHub repos filtered by AI/ML keywords using RSS feeds."
    )

    def _run(self, limit: int = 10) -> str:
        cfg = get_source_config("github_trending")
        cfg["max_items"] = min(limit, 20)
        items = github_fetch(cfg)

        result = []
        for item in items[:limit]:
            result.append(
                {
                    "type": "repo",
                    "source": item.source,
                    "title": item.title,
                    "url": item.url,
                    "summary": item.summary,
                }
            )

        return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    tool = GitHubRSSTool()
    print(tool.run(5))
