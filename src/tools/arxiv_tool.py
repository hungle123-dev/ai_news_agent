from langchain_core.tools import tool
from src.sources.arxiv import ArxivSource

@tool("arxiv_tool")
def arxiv_tool(limit: int = 3) -> list[dict]:
    """Tìm kiếm các bài báo nghiên cứu AI/ML mới nhất trên Arxiv."""
    src = ArxivSource()
    return [i.model_dump() for i in src.gather(limit=limit)]
