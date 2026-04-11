from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta

import requests
from openai import OpenAI
from pydantic import BaseModel, Field

from src.config import get_settings, prepare_runtime_environment
from src.models import PaperResearchItem, PaperStructuredSummary


prepare_runtime_environment()

from crewai.tools import BaseTool


HF_DAILY_PAPERS_API = "https://huggingface.co/api/daily_papers"


class HFDailyPapersToolInput(BaseModel):
    limit: int = Field(default=8, ge=1, le=20)
    date: str | None = Field(
        default=None,
        description="Ngày theo định dạng YYYY-MM-DD. Nếu bỏ trống sẽ tự thử hôm nay và hôm qua.",
    )


def _parse_target_date(target_date: str | None) -> date:
    if not target_date:
        return date.today() - timedelta(days=1)
    try:
        return datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        return date.today() - timedelta(days=1)


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def _candidate_dates(target_date: str | None) -> list[str]:
    base_date = _parse_target_date(target_date)
    return [
        base_date.strftime("%Y-%m-%d"),
        (base_date - timedelta(days=1)).strftime("%Y-%m-%d"),
    ]


def get_daily_papers(
    target_date: str | None = None,
    page: int = 1,
    limit: int = 20,
    session: requests.Session | None = None,
) -> list[dict]:
    active_session = session or _build_session()

    for candidate in _candidate_dates(target_date):
        try:
            response = active_session.get(
                HF_DAILY_PAPERS_API,
                params={"date": candidate, "page": page, "limit": limit},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            continue

        papers = payload.get("papers") if isinstance(payload, dict) else payload
        if isinstance(papers, list) and papers:
            return papers

    return []


def normalize_daily_paper(payload: dict) -> dict:
    paper = payload.get("paper", payload)
    paper_id = paper.get("id") or paper.get("paper_id") or "unknown"
    default_url = f"https://huggingface.co/papers/{paper_id}"

    paper_url = (
        paper.get("url")
        or paper.get("paper_url")
        or payload.get("url")
        or default_url
    )
    if paper_url == default_url and re.match(r"^\d{4}\.\d{4,5}$", str(paper_id)):
        paper_url = f"https://arxiv.org/abs/{paper_id}"

    return {
        "title": paper.get("title", "").strip(),
        "summary": (paper.get("summary") or paper.get("abstract") or "").strip(),
        "keywords": paper.get("ai_keywords") or [],
        "upvotes": int(paper.get("upvotes", 0) or 0),
        "url": paper_url,
    }


def _fallback_paper_summary(normalized: dict) -> PaperStructuredSummary:
    summary = normalized["summary"] or "Chưa có abstract rõ ràng từ nguồn gốc."
    keywords = normalized["keywords"] or ["AI", "research", "paper"]
    return PaperStructuredSummary(
        title=normalized["title"] or "Unknown paper",
        summary_vi=summary[:200],
        core_idea=summary[:300],
        keywords=keywords,
        impact="Cần đọc thêm abstract đầy đủ để đánh giá tác động.",
    )


def _build_paper_prompt(title: str, summary: str) -> str:
    return f"""
Bạn là hệ thống phân tích paper AI cho bản tin kỹ thuật.

Yêu cầu:
- Dịch và tóm tắt sang tiếng Việt.
- Không bịa thông tin ngoài title/abstract.
- Không markdown.
- `summary_vi` dưới 60 từ.
- `keywords` có từ 3 đến 5 phần tử.

Paper:
Title: {title}

Abstract:
{summary[:16000]}
"""


def extract_paper_info(
    title: str,
    summary: str,
    client: OpenAI | None = None,
    model: str | None = None,
    max_retries: int = 2,
) -> PaperStructuredSummary:
    normalized = {"title": title, "summary": summary, "keywords": []}
    if not client:
        return _fallback_paper_summary(normalized)

    model_name = model or get_settings().openai_model

    for _ in range(max_retries):
        try:
            response = client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là hệ thống phân tích paper AI. Chỉ trả về JSON hợp lệ.",
                    },
                    {
                        "role": "user",
                        "content": _build_paper_prompt(title, summary),
                    },
                ],
                response_format=PaperStructuredSummary,
                temperature=0.2,
            )
            message = response.choices[0].message
            if message.parsed:
                return message.parsed
        except Exception:
            continue

    return _fallback_paper_summary(normalized)


def collect_daily_paper_summaries(
    limit: int = 8,
    target_date: str | None = None,
    session: requests.Session | None = None,
    client: OpenAI | None = None,
) -> list[PaperResearchItem]:
    settings = get_settings()
    active_session = session or _build_session()
    openai_client = client
    if openai_client is None and settings.has_openai:
        openai_client = settings.build_openai_client()

    raw_papers = get_daily_papers(
        target_date=target_date,
        limit=limit,
        session=active_session,
    )

    results: list[PaperResearchItem] = []
    for payload in raw_papers[:limit]:
        normalized = normalize_daily_paper(payload)
        summary = extract_paper_info(
            normalized["title"],
            normalized["summary"],
            client=openai_client,
        )
        results.append(
            PaperResearchItem(
                title=summary.title or normalized["title"],
                url=normalized["url"],
                summary_vi=summary.summary_vi,
                core_idea=summary.core_idea,
                keywords=summary.keywords or normalized["keywords"],
                impact=summary.impact,
                upvotes=normalized["upvotes"],
            )
        )

    return results


class HuggingFaceDailyPapersTool(BaseTool):
    name: str = "huggingface_daily_papers_tool"
    description: str = (
        "Lấy Daily Papers từ Hugging Face theo ngày và trả về JSON tiếng Việt "
        "đã có tóm tắt ngắn, core idea, keywords và impact."
    )
    args_schema: type[BaseModel] = HFDailyPapersToolInput

    def _run(self, limit: int = 8, date: str | None = None) -> str:
        papers = collect_daily_paper_summaries(limit=limit, target_date=date)
        return json.dumps(
            [paper.model_dump() for paper in papers],
            ensure_ascii=False,
            indent=2,
        )


__all__ = [
    "HuggingFaceDailyPapersTool",
    "collect_daily_paper_summaries",
    "extract_paper_info",
    "get_daily_papers",
    "normalize_daily_paper",
]
