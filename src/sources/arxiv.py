import logging
from src.sources.base import Item, http_get

logger = logging.getLogger(__name__)

def fetch(cfg: dict) -> list[Item]:
    limit = cfg.get("max_items", 3)
    url = "http://export.arxiv.org/api/query"
    params = "search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=" + str(limit * 2)
    
    results = []
    try:
        from bs4 import BeautifulSoup
        resp = http_get(f"{url}?{params}")
        if resp:
            soup = BeautifulSoup(resp.text, 'xml')
            for entry in soup.find_all('entry'):
                title = entry.title.text.strip().replace('\n', ' ')
                link = entry.id.text.strip()
                summary = entry.summary.text.strip().replace('\n', ' ')
                
                results.append(Item(
                    source="Arxiv",
                    title=f"[Arxiv] {title}",
                    url=link,
                    summary=f"Paper nghiên cứu AI/ML mới trên Arxiv. Tóm tắt: {summary[:200]}..."
                ))
    except Exception as e:
        logger.error(f"Lỗi khi crawl Arxiv: {e}")
        
    return results[:limit]
