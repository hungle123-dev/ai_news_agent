import json
from crewai.tools import BaseTool
from src.sources.arxiv import fetch

class ArxivTool(BaseTool):
    name: str = "Arxiv Tool"
    description: str = "Tìm kiếm các bài báo nghiên cứu AI/ML mới nhất trên Arxiv."

    def _run(self, limit: int = 3) -> str:
        cfg = {"max_items": limit}
        items = fetch(cfg)
        result = [
            {"type": "article", "source": item.source, "title": item.title, "url": item.url, "summary": item.summary}
            for item in items
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)

arxiv_tool = ArxivTool()
