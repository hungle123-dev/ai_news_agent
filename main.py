from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from src.crew import AINewsCrew
from src.config import get_settings
from src.gateway.service import build_gateway, get_active_platforms
from src.monitoring import record_pipeline_run
from src.services.telegram_service import (
    TelegramService,
    publish_to_telegraph,
)
from src.utils import setup_logging
from src.helpers import extract_message_html
from src.state import (
    load_state,
    save_state,
    add_seen,
    get_stats,
    clear_state,
    STATE_DIR,
    STATE_FILE,
)

logger = logging.getLogger(__name__)

file_logger = setup_logging("ai-news")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AI news agent pipeline.")
    parser.add_argument("--repo-limit", type=int, default=None)
    parser.add_argument("--paper-limit", type=int, default=None)
    parser.add_argument("--paper-date", type=_paper_date_arg, default=None)
    parser.add_argument(
        "--send",
        action="store_true",
        help="Gửi message sau khi pipeline hoàn thành.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Lưu HTML cuối cùng ra file.",
    )
    parser.add_argument(
        "--telegraph",
        action="store_true",
        help="Gửi qua Telegraph (1 tin nhắn thay vì nhiều tin).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only - không gửi đi đâu.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Xóa state file (seen.json).",
    )
    parser.add_argument(
        "--init-state",
        action="store_true",
        help="Đánh dấu tất cả items hiện tại là đã thấy (seen).",
    )
    parser.add_argument(
        "--show-state",
        action="store_true",
        help="Hiển thị state stats.",
    )
    return parser


def _paper_date_arg(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "paper-date phải có định dạng YYYY-MM-DD."
        ) from exc
    return value


def run() -> str:
    args = build_parser().parse_args()
    settings = get_settings()

    # State management commands
    if args.reset_state:
        if clear_state():
            print("✅ State cleared.")
            file_logger.info("State cleared by user")
        else:
            print("No state to clear.")
        return ""

    if args.show_state:
        state = load_state()
        stats = get_stats(state)
        print(f"📊 State Stats:")
        print(f"  Seen items: {stats['seen_count']}")
        print(f"  Last run: {stats['last_run'] or 'Never'}")
        print(f"  State file: {STATE_FILE}")
        return ""

    # Dry-run: chỉ chạy crew và preview, không gửi đi đâu
    if args.dry_run:
        file_logger.info("🚀 Dry-run mode - Preview only")
        repo_limit = args.repo_limit or settings.default_repo_limit
        paper_limit = args.paper_limit or settings.default_paper_limit

        crew = AINewsCrew(
            repo_limit=repo_limit,
            paper_limit=paper_limit,
            paper_date=args.paper_date,
        )

        if args.telegraph:
            try:
                curated = crew.get_curated_newsletter()
                title = curated.headline if curated.headline else "AI News"
                message_html = f"<b>{title}</b>\n\n{curated.lead or ''}"
                print(f"\n📰 DRY-RUN PREVIEW (Telegraph mode):\n{message_html}\n")
                file_logger.info(f"Dry-run: {title} - ready for telegraph")
            except Exception as e:
                print(f"❌ Error in dry-run: {e}")
                file_logger.error(f"Dry-run failed: {e}")
        else:
            crew_output = crew.crew().kickoff()
            message_html = extract_message_html(crew_output)
            print(f"\n📰 DRY-RUN PREVIEW:\n{message_html}\n")
            title = (
                crew_output.pydantic.title
                if hasattr(crew_output.pydantic, "title")
                else "AI News"
            )
            file_logger.info(f"Dry-run: {title} - ready for preview")

        return message_html

    repo_limit = args.repo_limit or settings.default_repo_limit
    paper_limit = args.paper_limit or settings.default_paper_limit

    crew = AINewsCrew(
        repo_limit=repo_limit,
        paper_limit=paper_limit,
        paper_date=args.paper_date,
    )

    if args.send and args.telegraph:
        curated = crew.get_curated_newsletter()
        title = curated.headline if curated.headline else "AI News"
        telegraph_url = publish_to_telegraph(title, curated=curated)
        if telegraph_url:
            preview = f"<b>{title}</b>\n\n👉 <a href='{telegraph_url}'>Đọc chi tiết (Instant View)</a>"
            TelegramService().send_html_message(preview)
            print(f"✅ telegraph: {telegraph_url}")
        else:
            print("❌ telegraph: failed to publish")
        message_html = f"<b>{title}</b>\n\n{curated.lead or ''}"
    else:
        crew_output = crew.crew().kickoff()
        message_html = extract_message_html(crew_output)

        if args.send:
            title = (
                crew_output.pydantic.title
                if hasattr(crew_output.pydantic, "title")
                else "AI News"
            )
            active_platforms = get_active_platforms()

            if not active_platforms:
                print("⚠️  Không có platform nào được bật. Kiểm tra cấu hình .env")

            gateway = build_gateway()
            gateway.connect_all()

            results = gateway.deliver_newsletter(
                message_html, platforms=active_platforms if active_platforms else None
            )

            for platform, result in results.items():
                status = "✅" if result.success else "❌"
                print(f"{status} {platform}: {result.error or result.message_id}")

            record_pipeline_run(
                model=settings.openai_model
                if settings.llm_provider == "openai"
                else settings.gemini_model,
                provider=settings.llm_provider,
                repo_count=repo_limit,
                paper_count=paper_limit,
                success=any(r.success for r in results.values()),
            )

    if args.output_file:
        args.output_file.write_text(message_html, encoding="utf-8")

    print(message_html)
    return message_html


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        logger.error(f"Pipeline failed: {exc}")
        print("❌ Pipeline failed. Check logs for details.")
        raise SystemExit(1)
