"""
settings.py — Unified settings: load .env, parse config.yaml, build LLM.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

LOG_DIR = Path.home() / ".ai-news"
LOG_DIR.mkdir(parents=True, exist_ok=True)

CREWAI_STORAGE = ROOT / ".crewai"
CREWAI_STORAGE.mkdir(parents=True, exist_ok=True)

# Tắt telemetry/tracing của CrewAI ngay khi import
os.environ.setdefault("CREWAI_STORAGE_DIR", str(CREWAI_STORAGE))
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")


# ── Logging ────────────────────────────────────────────────────────────────────
def setup_logging(name: str = "ai-news") -> logging.Logger:
    """Setup file + console logging. Idempotent."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(LOG_DIR / "radar.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ── Config YAML ────────────────────────────────────────────────────────────────
def load_config() -> dict:
    """Load config.yaml từ thư mục gốc dự án."""
    path = ROOT / "config.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text("utf-8")) or {}


def get_source_config(source_name: str) -> dict:
    """Lấy config cho một nguồn cụ thể từ config.yaml."""
    return load_config().get("sources", {}).get(source_name, {})


# ── Settings dataclass ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Settings:
    # LLM
    llm_provider: str         # "openai" | "gemini"
    openai_key: str | None
    gemini_key: str | None
    openai_model: str
    gemini_model: str

    # GitHub
    github_token: str | None

    # Telegram
    telegram_token: str | None
    chat_id: str | None

    # Discord
    discord_webhook_url: str | None

    # Email
    email_smtp_host: str | None
    email_smtp_port: int
    email_username: str | None
    email_password: str | None
    email_from: str | None
    email_to: str | None

    # Feature flags (từ .env)
    enable_telegram: bool
    enable_discord: bool
    enable_email: bool

    # Limits
    default_repo_limit: int

    # Derived
    @property
    def has_openai(self) -> bool:
        return bool(self.openai_key)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.chat_id)

    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_webhook_url)

    @property
    def email_enabled(self) -> bool:
        return bool(self.email_username and self.email_to)

    def build_llm(self, temperature: float = 0.2):
        """Tạo CrewAI LLM object."""
        from crewai import LLM

        if self.llm_provider == "openai":
            return LLM(model=self.openai_model, api_key=self.openai_key,
                       temperature=temperature)
        return LLM(model=self.gemini_model, api_key=self.gemini_key,
                   temperature=temperature)

    def build_openai_client(self):
        """Tạo OpenAI client (chỉ dùng khi provider = openai)."""
        from openai import OpenAI
        return OpenAI(api_key=self.openai_key)


def _detect_provider() -> str:
    prov = os.getenv("AI_NEWS_LLM_PROVIDER", "auto").lower()
    if prov == "openai" or (prov == "auto" and os.getenv("OPENAI_API_KEY")):
        return "openai"
    if prov == "gemini" or (prov == "auto" and os.getenv("GEMINI_API_KEY")):
        return "gemini"
    raise RuntimeError("Cần OPENAI_API_KEY hoặc GEMINI_API_KEY trong file .env")


def _int_env(name: str, default: int) -> int:
    """Safely parse int env var — returns default if missing or empty string."""
    val = (os.getenv(name) or "").strip()
    return int(val) if val else default


def _str_env(name: str) -> str | None:
    """Return None if env var is missing or empty string."""
    val = (os.getenv(name) or "").strip()
    return val if val else None


def _bool_env(name: str, default: bool) -> bool:
    """Safely parse bool env var — handles empty string."""
    val = (os.getenv(name) or "").strip().lower()
    if not val:
        return default
    return val == "true"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton Settings — load một lần, cache mãi."""
    return Settings(
        llm_provider=_detect_provider(),
        openai_key=_str_env("OPENAI_API_KEY"),
        gemini_key=_str_env("GEMINI_API_KEY"),
        openai_model=_str_env("AI_NEWS_OPENAI_MODEL") or "gpt-4o-mini",
        gemini_model=_str_env("AI_NEWS_GEMINI_MODEL") or "gemini-2.0-flash",
        github_token=_str_env("GITHUB_TOKEN"),
        telegram_token=_str_env("TELEGRAM_TOKEN"),
        chat_id=_str_env("CHAT_ID"),
        discord_webhook_url=_str_env("DISCORD_WEBHOOK_URL"),
        email_smtp_host=_str_env("EMAIL_SMTP_HOST"),
        email_smtp_port=_int_env("EMAIL_SMTP_PORT", 587),
        email_username=_str_env("EMAIL_USERNAME"),
        email_password=_str_env("EMAIL_PASSWORD"),
        email_from=_str_env("EMAIL_FROM"),
        email_to=_str_env("EMAIL_TO"),
        enable_telegram=_bool_env("ENABLE_TELEGRAM", True),
        enable_discord=_bool_env("ENABLE_DISCORD", False),
        enable_email=_bool_env("ENABLE_EMAIL", False),
        default_repo_limit=_int_env("AI_NEWS_REPO_LIMIT", 5),
    )
