from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def prepare_runtime_environment() -> Path:
    storage_dir = ROOT_DIR / ".crewai"
    storage_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CREWAI_STORAGE_DIR", str(storage_dir))
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    return storage_dir


@dataclass(frozen=True)
class RuntimeSettings:
    root_dir: Path
    crewai_storage_dir: Path
    openai_api_key: str | None
    gemini_api_key: str | None
    github_token: str | None
    telegram_token: str | None
    chat_id: str | None
    discord_webhook_url: str | None
    email_smtp_host: str | None
    email_smtp_port: int | None
    email_username: str | None
    email_password: str | None
    email_from: str | None
    email_to: str | None
    llm_provider: str
    openai_model: str
    gemini_model: str
    default_repo_limit: int
    default_paper_limit: int
    enable_telegram: bool
    enable_discord: bool
    enable_email: bool

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.chat_id)

    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_webhook_url)

    @property
    def email_enabled(self) -> bool:
        return bool(
            self.email_smtp_host and self.email_username and 
            self.email_password and self.email_to
        )

    def build_openai_client(self) -> OpenAI:
        if not self.openai_api_key:
            raise RuntimeError("Thiếu OPENAI_API_KEY nên không thể dùng structured summary.")
        return OpenAI(api_key=self.openai_api_key)

    def build_crewai_llm(self, temperature: float = 0.2):
        prepare_runtime_environment()
        from crewai import LLM

        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise RuntimeError("Thiếu OPENAI_API_KEY cho CrewAI.")
            return LLM(
                model=self.openai_model,
                provider="openai",
                api_key=self.openai_api_key,
                temperature=temperature,
            )

        if self.llm_provider == "gemini":
            if not self.gemini_api_key:
                raise RuntimeError("Thiếu GEMINI_API_KEY cho CrewAI.")
            return LLM(
                model=self.gemini_model,
                provider="gemini",
                api_key=self.gemini_api_key,
                temperature=temperature,
            )

        raise RuntimeError(f"Provider không hỗ trợ: {self.llm_provider}")


def _detect_llm_provider() -> str:
    provider = (os.getenv("AI_NEWS_LLM_PROVIDER") or "auto").strip().lower()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if provider not in {"auto", "openai", "gemini"}:
        raise ValueError(
            "AI_NEWS_LLM_PROVIDER chỉ được phép là auto, openai hoặc gemini."
        )

    if provider == "openai":
        return "openai"
    if provider == "gemini":
        return "gemini"
    if openai_api_key:
        return "openai"
    if gemini_api_key:
        return "gemini"

    raise RuntimeError(
        "Cần ít nhất một API key cho OPENAI_API_KEY hoặc GEMINI_API_KEY."
    )


@lru_cache(maxsize=1)
def get_settings() -> RuntimeSettings:
    storage_dir = prepare_runtime_environment()
    return RuntimeSettings(
        root_dir=ROOT_DIR,
        crewai_storage_dir=storage_dir,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        github_token=os.getenv("GITHUB_TOKEN"),
        telegram_token=os.getenv("TELEGRAM_TOKEN"),
        chat_id=os.getenv("CHAT_ID"),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        email_smtp_host=os.getenv("EMAIL_SMTP_HOST"),
        email_smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
        email_username=os.getenv("EMAIL_USERNAME"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_from=os.getenv("EMAIL_FROM"),
        email_to=os.getenv("EMAIL_TO"),
        llm_provider=_detect_llm_provider(),
        openai_model=os.getenv("AI_NEWS_OPENAI_MODEL", "gpt-4o-mini"),
        gemini_model=os.getenv("AI_NEWS_GEMINI_MODEL", "gemini-2.0-flash"),
        default_repo_limit=int(os.getenv("AI_NEWS_REPO_LIMIT", "5")),
        default_paper_limit=int(os.getenv("AI_NEWS_PAPER_LIMIT", "8")),
        enable_telegram=os.getenv("ENABLE_TELEGRAM", "true").lower() == "true",
        enable_discord=os.getenv("ENABLE_DISCORD", "false").lower() == "true",
        enable_email=os.getenv("ENABLE_EMAIL", "false").lower() == "true",
    )
