from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RepoStructuredSummary(BaseModel):
    repo_name: str = Field(description="Tên repository")
    one_liner: str = Field(description="Tóm tắt ngắn, tối đa 20 từ")
    core_problem_solved: str = Field(description="Bài toán chính repo giải quyết")
    key_innovations: list[str] = Field(
        default_factory=list,
        description="Ba điểm nổi bật quan trọng nhất",
    )
    technical_highlights: str = Field(
        description="Tech stack, kiến trúc hoặc điểm kỹ thuật đáng chú ý",
    )

    @field_validator("key_innovations")
    @classmethod
    def normalize_key_innovations(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned:
            cleaned = ["Không rõ"]
        while len(cleaned) < 3:
            cleaned.append("Không rõ")
        return cleaned[:3]


class PaperStructuredSummary(BaseModel):
    title: str = Field(description="Tên paper")
    summary_vi: str = Field(description="Tóm tắt tiếng Việt ngắn gọn")
    core_idea: str = Field(description="Ý tưởng chính")
    keywords: list[str] = Field(
        default_factory=list,
        description="Ba đến năm từ khóa quan trọng",
    )
    impact: str = Field(description="Tác động hoặc ứng dụng tiềm năng")

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned:
            cleaned = ["AI"]
        return cleaned[:5]


class RepoResearchItem(BaseModel):
    type: Literal["repo"] = "repo"
    repo_path: str
    repo_name: str
    repo_url: str
    description: str
    language: str | None = None
    stars_today: int | None = None
    one_liner: str
    core_problem_solved: str
    key_innovations: list[str]
    technical_highlights: str


class PaperResearchItem(BaseModel):
    type: Literal["paper"] = "paper"
    title: str
    url: str
    summary_vi: str
    core_idea: str
    keywords: list[str]
    impact: str
    upvotes: int = 0


class ResearchCollection(BaseModel):
    generated_at: str
    repos: list[RepoResearchItem] = Field(default_factory=list)
    papers: list[PaperResearchItem] = Field(default_factory=list)


class NewsletterEntry(BaseModel):
    kind: Literal["repo", "paper"]
    title: str
    url: str
    tldr: str
    why_it_matters: str
    highlights: list[str] = Field(default_factory=list)
    source_signal: str | None = None

    @field_validator("highlights")
    @classmethod
    def normalize_highlights(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        return cleaned[:3]


class CuratedNewsletter(BaseModel):
    headline: str
    lead: str
    repos: list[NewsletterEntry] = Field(default_factory=list)
    papers: list[NewsletterEntry] = Field(default_factory=list)


class FormattedNewsletter(BaseModel):
    title: str
    message_html: str
