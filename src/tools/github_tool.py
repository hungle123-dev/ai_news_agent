from __future__ import annotations

import base64
import json
import re
from typing import Any

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from pydantic import BaseModel, Field

from src.config import get_settings, prepare_runtime_environment
from src.models import RepoResearchItem, RepoStructuredSummary


prepare_runtime_environment()

from crewai.tools import BaseTool


AI_REPO_KEYWORDS = (
    "ai",
    "agent",
    "agentic",
    "llm",
    "gpt",
    "rag",
    "inference",
    "machine learning",
    "deep learning",
    "multimodal",
    "embedding",
    "transformer",
)


class TrendingRepoCandidate(BaseModel):
    repo_path: str
    repo_url: str
    description: str = ""
    language: str | None = None
    stars_today: int | None = None

    @property
    def repo_name(self) -> str:
        return self.repo_path.split("/")[-1]


class GithubTrendingToolInput(BaseModel):
    limit: int = Field(default=5, ge=1, le=10)


def _build_session(github_token: str | None = None) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github+json",
        }
    )
    if github_token:
        session.headers["Authorization"] = f"Bearer {github_token}"
    return session


def _decode_base64(content: str) -> str:
    return base64.b64decode(content).decode("utf-8", errors="ignore")


def _extract_stars_today(article: Any) -> int | None:
    text = article.get_text(" ", strip=True)
    match = re.search(r"([\d,]+)\s+stars?\s+today", text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _is_ai_related_text(*parts: str | None) -> bool:
    merged = " ".join(part.strip().lower() for part in parts if part)
    return any(keyword in merged for keyword in AI_REPO_KEYWORDS)


def parse_trending_repos_from_html(html: str) -> list[TrendingRepoCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[TrendingRepoCandidate] = []

    for article in soup.find_all("article", class_="Box-row"):
        header = article.find("h2")
        anchor = header.find("a") if header else None
        if anchor is None or not anchor.get("href"):
            continue

        repo_path = anchor["href"].strip().strip("/")
        description_tag = article.find("p")
        language_tag = article.find("span", attrs={"itemprop": "programmingLanguage"})

        candidates.append(
            TrendingRepoCandidate(
                repo_path=repo_path,
                repo_url=f"https://github.com/{repo_path}",
                description=description_tag.get_text(" ", strip=True)
                if description_tag
                else "",
                language=language_tag.get_text(" ", strip=True) if language_tag else None,
                stars_today=_extract_stars_today(article),
            )
        )

    return candidates


def get_daily_trending_repos(
    limit: int = 5,
    session: requests.Session | None = None,
    github_token: str | None = None,
) -> list[TrendingRepoCandidate]:
    active_session = session or _build_session(github_token)
    try:
        response = active_session.get(
            "https://github.com/trending?since=daily",
            timeout=15,
            headers={"Accept": "text/html"},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    parsed = parse_trending_repos_from_html(response.text)
    ai_first = [
        item for item in parsed if _is_ai_related_text(item.repo_path, item.description)
    ]
    chosen = ai_first or parsed
    return chosen[: max(limit * 3, limit)]


def fetch_readme(
    repo_path: str,
    session: requests.Session | None = None,
    github_token: str | None = None,
) -> str | None:
    active_session = session or _build_session(github_token)
    api_url = f"https://api.github.com/repos/{repo_path}/readme"

    try:
        response = active_session.get(api_url, timeout=15)
        if response.status_code == 200:
            payload = response.json()
            content = payload.get("content")
            if content:
                return _decode_base64(content)
    except requests.RequestException:
        pass

    try:
        contents_response = active_session.get(
            f"https://api.github.com/repos/{repo_path}/contents",
            timeout=15,
        )
        if contents_response.status_code == 200:
            for item in contents_response.json():
                if "readme" in item.get("name", "").lower() and item.get("download_url"):
                    raw_response = active_session.get(item["download_url"], timeout=15)
                    if raw_response.status_code == 200:
                        return raw_response.text
    except requests.RequestException:
        pass

    return None


def _fallback_repo_summary(candidate: TrendingRepoCandidate) -> RepoStructuredSummary:
    short_description = candidate.description or "Repo đang nổi trên GitHub, chưa có mô tả rõ."
    return RepoStructuredSummary(
        repo_name=candidate.repo_name,
        one_liner=short_description[:120],
        core_problem_solved=short_description,
        key_innovations=[
            "Đang tăng độ chú ý nhanh trên GitHub Trending",
            f"Ngôn ngữ chính: {candidate.language or 'Không rõ'}",
            "Cần đọc README để lấy thêm chiều sâu kỹ thuật",
        ],
        technical_highlights=candidate.language or "Không rõ",
    )


def _build_repo_prompt(candidate: TrendingRepoCandidate, readme_text: str) -> str:
    return f"""
Bạn là hệ thống phân tích README GitHub cho bản tin AI dành cho developer Việt.

Yêu cầu:
- Chỉ dùng thông tin có trong metadata và README.
- Viết hoàn toàn bằng tiếng Việt tự nhiên.
- Không markdown.
- Không bịa thông tin.
- `one_liner` phải thật ngắn, tối đa 20 từ.
- `key_innovations` phải có đúng 3 ý.

Metadata repo:
- Name: {candidate.repo_name}
- Path: {candidate.repo_path}
- URL: {candidate.repo_url}
- Description: {candidate.description or "Không rõ"}
- Language: {candidate.language or "Không rõ"}
- Stars today: {candidate.stars_today or 0}

README:
==========
{readme_text[:20000]}
==========
"""


def extract_repo_info(
    candidate: TrendingRepoCandidate,
    readme_text: str | None,
    client: OpenAI | None = None,
    model: str | None = None,
    max_retries: int = 2,
) -> RepoStructuredSummary:
    if not readme_text or not client:
        return _fallback_repo_summary(candidate)

    model_name = model or get_settings().openai_model

    for _ in range(max_retries):
        try:
            response = client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là hệ thống trích xuất dữ liệu từ README GitHub. "
                            "Chỉ trả về JSON hợp lệ theo schema."
                        ),
                    },
                    {
                        "role": "user",
                        "content": _build_repo_prompt(candidate, readme_text),
                    },
                ],
                response_format=RepoStructuredSummary,
                temperature=0.1,
            )
            message = response.choices[0].message
            if message.parsed:
                return message.parsed
        except Exception:
            continue

    return _fallback_repo_summary(candidate)


def collect_trending_repo_summaries(
    limit: int = 5,
    session: requests.Session | None = None,
    client: OpenAI | None = None,
    github_token: str | None = None,
) -> list[RepoResearchItem]:
    settings = get_settings()
    active_session = session or _build_session(github_token or settings.github_token)

    openai_client = client
    if openai_client is None and settings.has_openai:
        openai_client = settings.build_openai_client()

    candidates = get_daily_trending_repos(
        limit=limit,
        session=active_session,
        github_token=github_token or settings.github_token,
    )
    if not candidates:
        return []

    selected: list[RepoResearchItem] = []
    for candidate in candidates:
        readme_text = fetch_readme(
            candidate.repo_path,
            session=active_session,
            github_token=github_token or settings.github_token,
        )
        summary = extract_repo_info(candidate, readme_text, client=openai_client)

        selected.append(
            RepoResearchItem(
                repo_path=candidate.repo_path,
                repo_name=summary.repo_name or candidate.repo_name,
                repo_url=candidate.repo_url,
                description=candidate.description or "Không rõ",
                language=candidate.language,
                stars_today=candidate.stars_today,
                one_liner=summary.one_liner,
                core_problem_solved=summary.core_problem_solved,
                key_innovations=summary.key_innovations,
                technical_highlights=summary.technical_highlights,
            )
        )
        if len(selected) >= limit:
            break

    return selected


class GithubTrendingRepoTool(BaseTool):
    name: str = "github_trending_ai_repo_tool"
    description: str = (
        "Lấy GitHub Trending theo ngày, lọc các repo AI/agentic và trả về JSON "
        "đã được tóm tắt từ README bằng tiếng Việt. Dùng khi cần repo nổi bật."
    )
    args_schema: type[BaseModel] = GithubTrendingToolInput

    def _run(self, limit: int = 5) -> str:
        try:
            repos = collect_trending_repo_summaries(limit=limit)
        except Exception:
            repos = []
        return json.dumps(
            [repo.model_dump() for repo in repos],
            ensure_ascii=False,
            indent=2,
        )


__all__ = [
    "GithubTrendingRepoTool",
    "RepoResearchItem",
    "TrendingRepoCandidate",
    "collect_trending_repo_summaries",
    "extract_repo_info",
    "fetch_readme",
    "get_daily_trending_repos",
    "parse_trending_repos_from_html",
]
