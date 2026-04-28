from langchain_core.tools import tool
from src.sources.hacker_news import HackerNewsSource

@tool("hacker_news_tool")
def hacker_news_tool(limit: int = 5) -> list[dict]:
    """Tìm kiếm các bài viết nổi bật trên Hacker News về chủ đề AI/LLM."""
    src = HackerNewsSource()
    return [i.model_dump() for i in src.gather(limit=limit)]
