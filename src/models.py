"""
models.py — Tất cả Pydantic models cho pipeline.

Stages:
  1. ResearchCollection   — dữ liệu thô từ researcher agent
  2. CuratedNewsletter    — bản tin đã chọn lọc từ analyst agent
  3. FormattedNewsletter  — HTML cuối cùng từ formatter agent
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Stage 1: Dữ liệu thô ──────────────────────────────────────────────────────

class RepoResearchItem(BaseModel):
    """Thông tin một GitHub repo đã được LLM tóm tắt."""
    type: Literal["repo"] = "repo"
    repo_path: str        # e.g. "openai/gpt-4"
    repo_name: str
    repo_url: str
    description: str
    language: str | None = None
    stars_today: int | None = None
    one_liner: str
    core_problem_solved: str
    key_innovations: list[str]
    technical_highlights: str


class ArticleResearchItem(BaseModel):
    """Thông tin một bài báo/tin tức từ RSS feed."""
    type: Literal["article"] = "article"
    source: str           # e.g. "Anthropic", "Security"
    title: str
    url: str
    published: str | None = None
    summary: str


class ResearchCollection(BaseModel):
    """Kết quả thu thập từ researcher agent."""
    generated_at: str
    repos: list[RepoResearchItem] = Field(default_factory=list)
    articles: list[ArticleResearchItem] = Field(default_factory=list)


# ── Stage 2: Bản tin đã chọn lọc ─────────────────────────────────────────────

class NewsletterEntry(BaseModel):
    """Một mục trong bản tin đã được curate."""
    kind: Literal["repo", "article"] = "repo"
    title: str
    url: str
    tldr: str
    why_it_matters: str
    highlights: list[str] = Field(default_factory=list)
    source_signal: str | None = None

    @field_validator("highlights")
    @classmethod
    def cap_highlights(cls, v: list[str]) -> list[str]:
        return [s.strip() for s in v if s and s.strip()][:3]


class CuratedNewsletter(BaseModel):
    """Bản tin đã chọn lọc, chưa format HTML."""
    headline: str
    lead: str
    repos: list[NewsletterEntry] = Field(default_factory=list)
    articles: list[NewsletterEntry] = Field(default_factory=list)


# ── Stage 3: HTML cuối cùng ───────────────────────────────────────────────────

class FormattedNewsletter(BaseModel):
    """Bản tin đã format HTML, sẵn sàng gửi."""
    title: str
    message_html: str


# ── Helper: LLM structured output từ README ───────────────────────────────────

class RepoStructuredSummary(BaseModel):
    """Schema dùng để parse structured output từ LLM khi đọc README."""
    repo_name: str
    one_liner: str
    core_problem_solved: str
    key_innovations: list[str] = Field(default_factory=list)
    technical_highlights: str

    @field_validator("key_innovations")
    @classmethod
    def ensure_three(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        while len(cleaned) < 3:
            cleaned.append("Không rõ")
        return cleaned[:3]
