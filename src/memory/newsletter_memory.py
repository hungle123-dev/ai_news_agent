from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class UserPreference(BaseModel):
    preferred_repo_count: int = Field(default=5, ge=1, le=20)
    preferred_paper_count: int = Field(default=8, ge=1, le=30)
    topics: list[str] = Field(default_factory=list)
    language: str = Field(default="vi")
    delivery_time: str = Field(default="09:00")
    platforms: list[str] = Field(default_factory=lambda: ["telegram"])


class NewsletterHistory(BaseModel):
    date: str
    headline: str
    repo_count: int
    paper_count: int
    delivery_status: str
    delivery_platforms: list[str]
    user_feedback: Optional[str] = None


class NewsletterMemory:
    MAX_HISTORY_ITEMS = 30
    MAX_SEEN_ITEMS = 100

    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or (Path.home() / ".ai_news_agent")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.storage_dir / "memory.json"
        self._load()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.memory_file.exists():
            self._save()

    def _load(self):
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self._memory = json.load(f)
        else:
            self._memory = {
                "preferences": UserPreference().model_dump(),
                "history": [],
                "seen_repos": [],
                "seen_papers": [],
                "created_at": datetime.now().isoformat(),
            }

    def _save(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self._memory, f, indent=2, ensure_ascii=False)

    def get_preferences(self) -> UserPreference:
        return UserPreference(**self._memory["preferences"])

    def update_preferences(self, **updates: dict):
        prefs = self.get_preferences()
        for key, value in updates.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        self._memory["preferences"] = prefs.model_dump()
        self._save()

    def add_to_history(self, newsletter: NewsletterHistory):
        self._memory["history"].append(newsletter.model_dump())
        if len(self._memory["history"]) > self.MAX_HISTORY_ITEMS:
            self._memory["history"] = self._memory["history"][-self.MAX_HISTORY_ITEMS :]
        self._save()

    def get_history(self, limit: int = 7) -> list[NewsletterHistory]:
        history = self._memory["history"][-limit:]
        return [NewsletterHistory(**h) for h in history]

    def mark_repo_seen(self, repo_path: str):
        if repo_path not in self._memory["seen_repos"]:
            self._memory["seen_repos"].append(repo_path)
            if len(self._memory["seen_repos"]) > self.MAX_SEEN_ITEMS:
                self._memory["seen_repos"] = self._memory["seen_repos"][-self.MAX_SEEN_ITEMS :]
            self._save()

    def mark_paper_seen(self, paper_id: str):
        if paper_id not in self._memory["seen_papers"]:
            self._memory["seen_papers"].append(paper_id)
            if len(self._memory["seen_papers"]) > self.MAX_SEEN_ITEMS:
                self._memory["seen_papers"] = self._memory["seen_papers"][-self.MAX_SEEN_ITEMS :]
            self._save()

    def is_repo_seen(self, repo_path: str) -> bool:
        return repo_path in self._memory["seen_repos"]

    def is_paper_seen(self, paper_id: str) -> bool:
        return paper_id in self._memory["seen_papers"]

    def get_fresh_repos(
        self, candidates: list[str], max_age_days: int = 7
    ) -> list[str]:
        fresh = [r for r in candidates if not self.is_repo_seen(r)]
        if len(fresh) < len(candidates) * 0.5:
            fresh = candidates
        return fresh[:20]

    def get_fresh_papers(
        self, candidates: list[str], max_age_days: int = 3
    ) -> list[str]:
        fresh = [p for p in candidates if not self.is_paper_seen(p)]
        if len(fresh) < len(candidates) * 0.3:
            fresh = candidates
        return fresh[:30]


_singleton: Optional[NewsletterMemory] = None


def get_memory() -> NewsletterMemory:
    global _singleton
    if _singleton is None:
        _singleton = NewsletterMemory()
    return _singleton