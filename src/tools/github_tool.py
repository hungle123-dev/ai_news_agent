"""
tools/github_tool.py — CrewAI tool thu thập GitHub Trending + tóm tắt README bằng LLM.

Flow:
  1. Scrape GitHub Trending page để lấy danh sách repo
  2. Fetch README của từng repo qua GitHub API
  3. Dùng LLM (OpenAI structured output) để tóm tắt README
  4. Trả về JSON list[RepoResearchItem]
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel

from src.models import RepoResearchItem, RepoStructuredSummary
from src.settings import get_settings

logger = logging.getLogger(__name__)

_TRENDING_URL = "https://github.com/trending"
_README_API = "https://api.github.com/repos/{repo_path}/readme"
_HEADERS = {"Accept": "application/vnd.github.v3.raw"}


# ── Data class cho repo từ trending page ──────────────────────────────────────

@dataclass
class TrendingRepo:
    repo_path: str    # e.g. "openai/gpt-4"
    repo_name: str    # e.g. "gpt-4"
    repo_url: str
    description: str
    language: str | None
    stars_today: int | None


# ── Input schema ──────────────────────────────────────────────────────────────

class GithubToolInput(BaseModel):
    limit: int = 5


# ── Scraping ──────────────────────────────────────────────────────────────────

def _build_session(github_token: str | None) -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (AI-News-Agent/1.0)"
    if github_token:
        session.headers["Authorization"] = f"token {github_token}"
    return session


def scrape_trending(
    limit: int = 10,
    session: requests.Session | None = None,
    github_token: str | None = None,
) -> list[TrendingRepo]:
    """Scrape trang GitHub Trending để lấy danh sách repo nổi bật."""
    from bs4 import BeautifulSoup

    s = session or _build_session(github_token)
    try:
        resp = s.get(_TRENDING_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch GitHub trending: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")

    repos: list[TrendingRepo] = []
    for article in articles[:limit * 2]:  # lấy dư để có đủ sau lọc
        try:
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            repo_path = h2["href"].lstrip("/")
            repo_name = repo_path.split("/")[-1]
            repo_url = f"https://github.com/{repo_path}"

            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            lang_el = article.select_one("[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else None

            stars_el = article.select_one("span.d-inline-block.float-sm-right")
            stars_today = None
            if stars_el:
                m = re.search(r"([\d,]+)", stars_el.get_text())
                if m:
                    stars_today = int(m.group(1).replace(",", ""))

            repos.append(TrendingRepo(
                repo_path=repo_path,
                repo_name=repo_name,
                repo_url=repo_url,
                description=description,
                language=language,
                stars_today=stars_today,
            ))
        except Exception:
            continue

    return repos[:limit]


def fetch_readme(
    repo_path: str,
    session: requests.Session | None = None,
    github_token: str | None = None,
) -> str | None:
    """Lấy nội dung README qua GitHub API."""
    s = session or _build_session(github_token)
    try:
        url = _README_API.format(repo_path=repo_path)
        resp = s.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.debug("README fetch failed for %s: %s", repo_path, e)
        return None


# ── LLM Summarization ─────────────────────────────────────────────────────────

def _fallback_summary(repo: TrendingRepo) -> RepoStructuredSummary:
    return RepoStructuredSummary(
        repo_name=repo.repo_name,
        one_liner=repo.description or "Không có mô tả",
        core_problem_solved=repo.description or "Không rõ",
        key_innovations=["Không rõ", "Không rõ", "Không rõ"],
        technical_highlights=f"Ngôn ngữ: {repo.language or 'Không rõ'}",
    )


def summarize_readme(
    repo: TrendingRepo,
    readme_text: str,
    openai_client,
    model: str,
    max_retries: int = 2,
) -> RepoStructuredSummary:
    """Dùng OpenAI structured output để tóm tắt README."""
    prompt = (
        f"Repo: {repo.repo_path}\n"
        f"Language: {repo.language or 'Không rõ'}\n"
        f"Stars today: {repo.stars_today or 0}\n\n"
        f"README:\n{'=' * 40}\n{readme_text[:20000]}\n{'=' * 40}"
    )

    for attempt in range(max_retries):
        try:
            response = openai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là hệ thống trích xuất dữ liệu từ README GitHub. "
                            "Chỉ trả về JSON hợp lệ theo schema."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=RepoStructuredSummary,
                temperature=0.1,
            )
            msg = response.choices[0].message
            if msg.parsed:
                return msg.parsed
        except Exception as e:
            logger.warning("LLM summarize attempt %d failed for %s: %s", attempt + 1, repo.repo_path, e)

    return _fallback_summary(repo)


# ── Main Collection Function ──────────────────────────────────────────────────

def collect_trending_repos(limit: int = 5) -> list[RepoResearchItem]:
    """Thu thập và tóm tắt GitHub trending repos."""
    settings = get_settings()
    session = _build_session(settings.github_token)

    openai_client = None
    if settings.has_openai:
        openai_client = settings.build_openai_client()

    repos = scrape_trending(limit=limit, session=session, github_token=settings.github_token)
    if not repos:
        return []

    results: list[RepoResearchItem] = []
    for repo in repos:
        readme = fetch_readme(repo.repo_path, session=session, github_token=settings.github_token)

        if readme and openai_client:
            summary = summarize_readme(repo, readme, openai_client, settings.openai_model)
        else:
            summary = _fallback_summary(repo)

        results.append(RepoResearchItem(
            repo_path=repo.repo_path,
            repo_name=summary.repo_name or repo.repo_name,
            repo_url=repo.repo_url,
            description=repo.description or "Không có mô tả",
            language=repo.language,
            stars_today=repo.stars_today,
            one_liner=summary.one_liner,
            core_problem_solved=summary.core_problem_solved,
            key_innovations=summary.key_innovations,
            technical_highlights=summary.technical_highlights,
        ))

        if len(results) >= limit:
            break

    return results


# ── CrewAI Tool ───────────────────────────────────────────────────────────────

class GithubTrendingRepoTool(BaseTool):
    name: str = "github_trending_ai_repo_tool"
    description: str = (
        "Lấy GitHub Trending theo ngày, lọc repo AI/agentic và tóm tắt README bằng LLM. "
        "Trả về JSON list các repo nổi bật. Dùng khi cần repo GitHub hôm nay."
    )
    args_schema: type[BaseModel] = GithubToolInput

    def _run(self, limit: int = 5) -> str:
        try:
            repos = collect_trending_repos(limit=limit)
        except Exception as e:
            logger.warning("GithubTrendingRepoTool failed: %s", e)
            repos = []
        return json.dumps([r.model_dump() for r in repos], ensure_ascii=False, indent=2)
