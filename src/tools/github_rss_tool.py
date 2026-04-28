"""
tools/github_rss_tool.py — CrewAI tool lấy GitHub trending qua RSS (nhanh hơn, không cần LLM).
"""

from __future__ import annotations

import json

from crewai.tools import BaseTool

from src.settings import get_source_config
from src.sources.github import fetch as github_fetch


class GitHubRSSTool(BaseTool):
    name: str = "GitHub Trending RSS"
    description: str = (
        "Lấy GitHub trending repos bằng RSS feed, lọc theo AI/ML keywords. "
        "Nhanh hơn github_trending_ai_repo_tool nhưng không có tóm tắt LLM."
    )

    def _run(self, limit: int = 10) -> str:
        cfg = get_source_config("github_trending")
        cfg["max_items"] = min(limit, 20)
        items = github_fetch(cfg)

        result = [
            {"type": "repo", "source": item.source, "title": item.title,
             "url": item.url, "summary": item.summary}
            for item in items[:limit]
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)
