import requests
import logging
from bs4 import BeautifulSoup
from src.sources.base import BaseSource, ArticleResearchItem

logger = logging.getLogger(__name__)

class ArxivSource(BaseSource):
    """Lấy các bài nghiên cứu mới nhất từ ArXiv (AI/ML)."""
    
    def gather(self, limit: int = 3, **kwargs) -> list[ArticleResearchItem]:
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": "cat:cs.AI OR cat:cs.LG",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": limit * 2
        }
        
        results = []
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'xml')
            
            for entry in soup.find_all('entry'):
                title = entry.title.text.strip().replace('\n', ' ')
                link = entry.id.text.strip()
                summary = entry.summary.text.strip().replace('\n', ' ')
                
                if self.is_seen(link):
                    continue
                    
                item = ArticleResearchItem(
                    title=f"[Arxiv] {title}",
                    url=link,
                    summary=f"Paper nghiên cứu AI/ML mới trên Arxiv. Tóm tắt: {summary[:200]}...",
                    source_signal="arxiv"
                )
                self.mark_seen(link)
                results.append(item)
                
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu từ Arxiv: {e}")
            
        return results
