from __future__ import annotations

import getpass
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def collect_telegram_config(
    prompt: bool = True,
) -> dict[str, Optional[str]]:
    if not prompt:
        return {"telegram_token": None, "chat_id": None}

    print("\n📱 Step 1: Telegram Configuration")
    print("-" * 40)
    print("Bạn cần lấy Bot Token từ @BotFather trên Telegram")
    print("Và Chat ID từ @userinfobot\n")

    token = input("Bot Token: ").strip()
    if not token:
        print("Bot Token không được để trống!")
        return collect_telegram_config(prompt=True)

    chat_id = input("Chat ID: ").strip()
    if not chat_id:
        print("Chat ID không được để trống!")
        return collect_telegram_config(prompt=True)

    return {"telegram_token": token, "chat_id": chat_id}


def collect_llm_config(prompt: bool = True) -> dict[str, Optional[str]]:
    if not prompt:
        return {
            "provider": "auto",
            "openai_api_key": None,
            "gemini_api_key": None,
        }

    print("\n🤖 Step 2: LLM Provider")
    print("-" * 40)
    print("Chọn provider để sử dụng:")
    print("  1. OpenAI (GPT-4o-mini)")
    print("  2. Gemini (Free tier)")
    print("  3. Cả hai (auto)\n")

    choice = input("Chọn (1/2/3): ").strip()

    config = {"provider": "auto", "openai_api_key": None, "gemini_api_key": None}

    if choice == "1":
        config["provider"] = "openai"
        key = getpass.getpass("OpenAI API Key: ").strip()
        config["openai_api_key"] = key or None
    elif choice == "2":
        config["provider"] = "gemini"
        key = getpass.getpass("Gemini API Key: ").strip()
        config["gemini_api_key"] = key or None
    else:
        key = getpass.getpass("OpenAI API Key: ").strip()
        config["openai_api_key"] = key or None
        key = getpass.getpass("Gemini API Key: ").strip()
        config["gemini_api_key"] = key or None

    return config


def collect_newsletter_preferences(prompt: bool = True) -> dict:
    if not prompt:
        return {
            "repo_limit": 5,
            "paper_limit": 8,
            "delivery_time": "09:00",
        }

    print("\n📰 Step 3: Newsletter Preferences")
    print("-" * 40)

    repo_limit = input("Số repo GitHub (mặc định 5): ").strip()
    paper_limit = input("Số paper HF (mặc định 8): ").strip()
    delivery_time = input("Giờ gửi (mặc định 09:00): ").strip()

    return {
        "repo_limit": int(repo_limit) if repo_limit else 5,
        "paper_limit": int(paper_limit) if paper_limit else 8,
        "delivery_time": delivery_time or "09:00",
    }


def generate_env_content(
    telegram_token: str,
    chat_id: str,
    provider: str,
    openai_api_key: Optional[str],
    gemini_api_key: Optional[str],
    repo_limit: int = 5,
    paper_limit: int = 8,
) -> str:
    lines = [
        "# AI News Agent Configuration",
        f"# Generated at: {Path(__file__).name}",
        "",
        "# Telegram",
        f"TELEGRAM_TOKEN={telegram_token}",
        f"CHAT_ID={chat_id}",
        "",
        "# LLM Provider",
        f"AI_NEWS_LLM_PROVIDER={provider}",
    ]

    if openai_api_key:
        lines.append(f"OPENAI_API_KEY={openai_api_key}")
    if gemini_api_key:
        lines.append(f"GEMINI_API_KEY={gemini_api_key}")

    lines.extend([
        "",
        "# Newsletter Settings",
        f"AI_NEWS_REPO_LIMIT={repo_limit}",
        f"AI_NEWS_PAPER_LIMIT={paper_limit}",
    ])

    return "\n".join(lines)


def run_setup():
    print("╔════════════════════════════════════════════════╗")
    print("║     AI News Agent - Setup Wizard              ║")
    print("╚════════════════════════════════════════════════╝\n")

    telegram_config = collect_telegram_config()
    if not telegram_config["telegram_token"]:
        print("❌ Cần Telegram token để tiếp tục!")
        return False

    llm_config = collect_llm_config()
    if not llm_config["openai_api_key"] and not llm_config["gemini_api_key"]:
        print("⚠️  Không có API key nào được cung cấp!")
        print("   Bạn sẽ cần thêm thủ công vào file .env")

    prefs = collect_newsletter_preferences()

    env_content = generate_env_content(
        telegram_token=telegram_config["telegram_token"],
        chat_id=telegram_config["chat_id"],
        provider=llm_config["provider"],
        openai_api_key=llm_config["openai_api_key"],
        gemini_api_key=llm_config["gemini_api_key"],
        repo_limit=prefs["repo_limit"],
        paper_limit=prefs["paper_limit"],
    )

    env_file = Path.home() / ".ai_news_agent" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(env_content, encoding="utf-8")

    print(f"\n✅ Setup hoàn tất!")
    print(f"   File cấu hình: {env_file}")
    print(f"\n   Để chạy agent:")
    print(f"   python main.py --send")
    return True


if __name__ == "__main__":
    run_setup()


__all__ = [
    "collect_telegram_config",
    "collect_llm_config",
    "collect_newsletter_preferences",
    "generate_env_content",
    "run_setup",
]