import json
from crewai.tools import BaseTool
from src.sources.youtube import fetch

class YouTubeTool(BaseTool):
    name: str = "YouTube AI Tool"
    description: str = "Lấy các video mới nhất từ các kênh YouTube AI hàng đầu (Fireship, AI Explained, Matt Wolfe, v.v.)."

    def _run(self, limit_per_channel: int = 1) -> str:
        # Default 1 video per channel (5 channels = 5 videos max) to keep context clean
        cfg = {"max_items": limit_per_channel}
        items = fetch(cfg)
        result = [
            {"type": "article", "source": item.source, "title": item.title, "url": item.url, "summary": item.summary}
            for item in items
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)
