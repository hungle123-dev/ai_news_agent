from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, Mock

import pytest

from src.setup.wizard import (
    collect_telegram_config,
    collect_llm_config,
    generate_env_content,
)


class TestCollectTelegramConfig:
    def test_prompts_for_token_and_chat_id(self):
        with patch("builtins.input", side_effect=["123456:ABCdefGHI", "987654321"]):
            with patch("src.setup.wizard.getpass.getpass", side_effect=["123456:ABCdefGHI", "987654321"]):
                config = collect_telegram_config()
        assert config["telegram_token"] == "123456:ABCdefGHI"
        assert config["chat_id"] == "987654321"


class TestCollectLLMConfig:
    def test_prompts_for_provider(self):
        with patch("builtins.input", return_value="1"):
            with patch("src.setup.wizard.getpass.getpass", return_value="sk-test-key"):
                config = collect_llm_config()
        assert config["provider"] == "openai"

    def test_prompts_for_openai_key(self):
        with patch("builtins.input", side_effect=["2", "sk-test-key"]):
            with patch("src.setup.wizard.getpass.getpass", side_effect=["sk-test-key"]):
                config = collect_llm_config()
        assert config["provider"] == "gemini"


class TestGenerateEnvContent:
    def test_generates_correct_env(self):
        content = generate_env_content(
            telegram_token="token",
            chat_id="123",
            provider="openai",
            openai_api_key="sk-key",
            gemini_api_key=None,
        )
        assert "TELEGRAM_TOKEN=token" in content
        assert "CHAT_ID=123" in content
        assert "OPENAI_API_KEY=sk-key" in content

    def test_includes_both_keys(self):
        content = generate_env_content(
            telegram_token="token",
            chat_id="123",
            provider="auto",
            openai_api_key="sk-openai",
            gemini_api_key="gemini-key",
        )
        assert "OPENAI_API_KEY=sk-openai" in content
        assert "GEMINI_API_KEY=gemini-key" in content