import requests
import logging
from src.sources.base import BaseSource, ArticleResearchItem

logger = logging.getLogger(__name__)

class HackerNewsSource(BaseSource):
    """Lấy tin tức nổi bật từ Hacker News (YCombinator) liên quan đến AI."""
    
    def gather(self, limit: int = 5, **kwargs) -> list[ArticleResearchItem]:
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": "AI OR LLM OR GPT OR OpenAI OR Anthropic OR Claude",
            "tags": "story",
            "numericFilters": "points>=20",
            "hitsPerPage": limit * 2
        }
        
        results = []
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            for hit in data.get("hits", []):
                title = hit.get("title", "")
                link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                points = hit.get("points", 0)
                
                if self.is_seen(link):
                    continue
                    
                item = ArticleResearchItem(
                    title=f"[HN] {title}",
                    url=link,
                    summary=f"Thảo luận trên Hacker News ({points} points) về các công nghệ AI/LLM mới.",
                    source_signal="hacker_news"
                )
                self.mark_seen(link)
                results.append(item)
                
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.error(f"Lỗi khi crawl Hacker News: {e}")
            
        return results
