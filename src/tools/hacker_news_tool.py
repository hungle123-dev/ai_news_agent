import json
from crewai.tools import BaseTool
from src.sources.hacker_news import fetch

class HackerNewsTool(BaseTool):
    name: str = "Hacker News Tool"
    description: str = "Tìm kiếm các bài viết nổi bật trên Hacker News về chủ đề AI/LLM."

    def _run(self, limit: int = 5) -> str:
        cfg = {"max_items": limit}
        items = fetch(cfg)
        result = [
            {"type": "article", "source": item.source, "title": item.title, "url": item.url, "summary": item.summary}
            for item in items
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)

hacker_news_tool = HackerNewsTool()
