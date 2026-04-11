from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.memory.newsletter_memory import (
    NewsletterHistory,
    NewsletterMemory,
    UserPreference,
    get_memory,
)


class TestUserPreference:
    def test_default_preferences(self):
        prefs = UserPreference()
        assert prefs.preferred_repo_count == 5
        assert prefs.preferred_paper_count == 8
        assert prefs.topics == []
        assert prefs.language == "vi"
        assert prefs.delivery_time == "09:00"
        assert prefs.platforms == ["telegram"]

    def test_custom_preferences(self):
        prefs = UserPreference(
            preferred_repo_count=10,
            preferred_paper_count=15,
            topics=["AI", "agent"],
            language="en",
            delivery_time="08:00",
            platforms=["telegram", "discord"],
        )
        assert prefs.preferred_repo_count == 10
        assert prefs.preferred_paper_count == 15
        assert prefs.topics == ["AI", "agent"]
        assert prefs.language == "en"
        assert prefs.delivery_time == "08:00"
        assert prefs.platforms == ["telegram", "discord"]


class TestNewsletterHistory:
    def test_history_creation(self):
        history = NewsletterHistory(
            date="2026-04-11",
            headline="Tin AI nổi bật",
            repo_count=5,
            paper_count=8,
            delivery_status="success",
            delivery_platforms=["telegram"],
        )
        assert history.date == "2026-04-11"
        assert history.headline == "Tin AI nổi bật"
        assert history.repo_count == 5
        assert history.paper_count == 8
        assert history.delivery_status == "success"
        assert history.delivery_platforms == ["telegram"]

    def test_history_with_feedback(self):
        history = NewsletterHistory(
            date="2026-04-11",
            headline="Tin AI",
            repo_count=5,
            paper_count=8,
            delivery_status="success",
            delivery_platforms=["telegram"],
            user_feedback="Rất hay!",
        )
        assert history.user_feedback == "Rất hay!"


class TestNewsletterMemory:
    @pytest.fixture
    def temp_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_memory_creation(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        assert memory.storage_dir == temp_storage
        memory_file = temp_storage / "memory.json"
        assert memory_file.exists()

    def test_default_preferences_loaded(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        prefs = memory.get_preferences()
        assert prefs.language == "vi"

    def test_update_preferences(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        memory.update_preferences(topics=["AI", "LLM"], delivery_time="08:30")
        prefs = memory.get_preferences()
        assert prefs.topics == ["AI", "LLM"]
        assert prefs.delivery_time == "08:30"

    def test_add_to_history(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        history = NewsletterHistory(
            date="2026-04-11",
            headline="Tin AI",
            repo_count=5,
            paper_count=8,
            delivery_status="success",
            delivery_platforms=["telegram"],
        )
        memory.add_to_history(history)
        loaded = memory.get_history(limit=1)
        assert len(loaded) == 1
        assert loaded[0].headline == "Tin AI"

    def test_history_limit_30(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        for i in range(35):
            memory.add_to_history(
                NewsletterHistory(
                    date=f"2026-04-{i:02d}",
                    headline=f"Tin {i}",
                    repo_count=5,
                    paper_count=8,
                    delivery_status="success",
                    delivery_platforms=["telegram"],
                )
            )
        loaded = memory.get_history(limit=35)
        assert len(loaded) == 30

    def test_mark_repo_seen(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        memory.mark_repo_seen("openai/agents-sdk")
        memory.mark_repo_seen("anthropic/claude-code")
        assert memory.is_repo_seen("openai/agents-sdk") is True
        assert memory.is_repo_seen("unknown/repo") is False

    def test_mark_paper_seen(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        memory.mark_paper_seen("2604.08377")
        memory.mark_paper_seen("2604.12345")
        assert memory.is_paper_seen("2604.08377") is True
        assert memory.is_paper_seen("9999.99999") is False

    def test_get_fresh_repos(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        candidates = ["a/b", "c/d", "e/f", "g/h"]
        memory.mark_repo_seen("a/b")
        fresh = memory.get_fresh_repos(candidates)
        assert "a/b" not in fresh
        assert "c/d" in fresh
        assert "e/f" in fresh
        assert "g/h" in fresh

    def test_get_fresh_repos_fallback_when_too_few(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        candidates = ["a/b", "c/d", "e/f"]
        memory.mark_repo_seen("a/b")
        memory.mark_repo_seen("c/d")
        memory.mark_repo_seen("e/f")
        fresh = memory.get_fresh_repos(candidates)
        assert fresh == candidates

    def test_get_fresh_papers(self, temp_storage):
        memory = NewsletterMemory(storage_dir=temp_storage)
        candidates = ["2604.00001", "2604.00002", "2604.00003"]
        memory.mark_paper_seen("2604.00001")
        fresh = memory.get_fresh_papers(candidates)
        assert "2604.00001" not in fresh
        assert "2604.00002" in fresh
        assert "2604.00003" in fresh


class TestGetMemorySingleton:
    def test_singleton_same_instance(self):
        with patch("src.memory.newsletter_memory._singleton", None):
            with patch.object(NewsletterMemory, "_load") as mock_load:
                mock_load.return_value = {
                    "preferences": UserPreference().model_dump(),
                    "history": [],
                    "seen_repos": [],
                    "seen_papers": [],
                    "created_at": datetime.now().isoformat(),
                }
                mem1 = get_memory()
                mem2 = get_memory()
        assert mem1 is mem2