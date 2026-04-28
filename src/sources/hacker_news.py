import logging
from src.sources.base import Item, http_get

logger = logging.getLogger(__name__)

def fetch(cfg: dict) -> list[Item]:
    limit = cfg.get("max_items", 5)
    url = "https://hn.algolia.com/api/v1/search"
    
    results = []
    try:
        resp = http_get(f"{url}?query=AI+OR+LLM+OR+GPT+OR+OpenAI+OR+Anthropic+OR+Claude&tags=story&numericFilters=points>=20&hitsPerPage={limit * 2}")
        if resp:
            data = resp.json()
            for hit in data.get("hits", []):
                title = hit.get("title", "")
                link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                points = hit.get("points", 0)
                
                results.append(Item(
                    source="Hacker News",
                    title=f"[HN] {title}",
                    url=link,
                    summary=f"Thảo luận trên Hacker News ({points} points) về các công nghệ AI/LLM mới."
                ))
    except Exception as e:
        logger.error(f"Lỗi khi crawl Hacker News: {e}")
        
    return results[:limit]
