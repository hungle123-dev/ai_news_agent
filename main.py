"""
main.py — Entry point của AI News Agent.

Cách dùng:
  python main.py --dry-run              # Preview, không gửi
  python main.py --send                 # Chạy và gửi Telegram
  python main.py --send --telegraph     # Gửi dạng Telegraph link
  python main.py --test-source github   # Test nguồn dữ liệu
  python main.py --show-state           # Xem trạng thái đã seen
  python main.py --reset-state          # Xóa state
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.settings import get_settings, setup_logging

logger = logging.getLogger(__name__)


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI News Agent — thu thập và gửi bản tin AI hàng ngày.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo-limit", type=int, default=None,
                        help="Số repo GitHub tối đa (default từ .env hoặc 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chạy và preview, KHÔNG gửi đi đâu")
    parser.add_argument("--send", action="store_true",
                        help="Chạy và gửi đến các platform đã cấu hình")
    parser.add_argument("--telegraph", action="store_true",
                        help="Gửi dạng Telegraph link thay vì HTML trực tiếp")
    parser.add_argument("--output-file", type=Path, default=None,
                        help="Lưu HTML ra file (vd: output.html)")
    parser.add_argument("--test-source", metavar="SOURCE",
                        choices=["github", "anthropic", "security"],
                        help="Test một nguồn dữ liệu cụ thể: github|anthropic|security")
    parser.add_argument("--show-state", action="store_true",
                        help="Xem thống kê state (số URL đã seen, lần chạy cuối)")
    parser.add_argument("--reset-state", action="store_true",
                        help="Xóa state file (seen.json)")
    return parser


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_show_state() -> None:
    from src.state import STATE_FILE, get_stats
    stats = get_stats()
    print(f"📊 State Stats:")
    print(f"  Seen items : {stats['seen_count']}")
    print(f"  Last run   : {stats['last_run'] or 'Chưa chạy lần nào'}")
    print(f"  State file : {STATE_FILE}")


def cmd_reset_state() -> None:
    from src.state import clear_state
    if clear_state():
        print("✅ State đã được xóa.")
    else:
        print("ℹ️  Không có state để xóa.")


def cmd_test_source(source_name: str) -> None:
    """Test một nguồn dữ liệu và in ra 5 items đầu tiên."""
    from src.settings import get_source_config

    cfg = get_source_config(source_name if source_name != "github" else "github_trending")

    if source_name == "github":
        from src.sources.github import fetch
    elif source_name == "anthropic":
        from src.sources.anthropic import fetch
    else:
        from src.sources.security import fetch

    items = fetch(cfg)
    print(f"📰 {source_name}: {len(items)} items")
    for item in items[:5]:
        print(f"  • {item.title[:70]}")
        print(f"    {item.url}")


def cmd_run(args: argparse.Namespace) -> str:
    """Chạy pipeline chính: gather → summarize → format → (gửi)."""
    from src.crew import AINewsCrew
    from src.delivery.telegram import extract_message_html, publish_to_telegraph
    from src.delivery.gateway import build_gateway, get_active_platforms

    settings = get_settings()
    repo_limit = args.repo_limit or settings.default_repo_limit

    crew = AINewsCrew(repo_limit=repo_limit)

    # ── Chế độ Telegraph (dùng get_curated_newsletter, không cần format_task) ──
    if args.telegraph:
        curated = crew.get_curated_newsletter()
        title = curated.headline or "AI News"

        if args.dry_run:
            print(f"\n📰 DRY-RUN (Telegraph mode)")
            print(f"Title: {title}")
            print(f"Repos: {len(curated.repos)}, Articles: {len(curated.articles)}")
            return title

        telegraph_url = publish_to_telegraph(title, curated=curated)
        if telegraph_url:
            preview = f"<b>{title}</b>\n\n👉 <a href='{telegraph_url}'>Đọc chi tiết</a>"
            _send_telegram_direct(preview, settings)
            print(f"✅ Telegraph: {telegraph_url}")
        else:
            print("❌ Telegraph: publish thất bại")
        return telegraph_url or ""

    # ── Chế độ thông thường (chạy full 3-task pipeline) ─────────────────────
    crew_output = crew.crew().kickoff()
    message_html = extract_message_html(crew_output)

    if args.dry_run:
        print(f"\n📰 DRY-RUN PREVIEW:\n{message_html}\n")
        logger.info("Dry-run hoàn thành")
        return message_html

    if args.send:
        active_platforms = get_active_platforms()
        if not active_platforms:
            print("⚠️  Không có platform nào được bật. Kiểm tra .env")
            return message_html

        gateway = build_gateway()
        results = gateway.deliver(message_html, platforms=active_platforms)

        for platform, result in results.items():
            icon = "✅" if result.success else "❌"
            detail = result.error or result.message_id or "OK"
            print(f"{icon} {platform}: {detail}")

        logger.info("Gửi xong: %s", {k: v.success for k, v in results.items()})

    # Lưu ra file nếu có
    if args.output_file:
        args.output_file.write_text(message_html, encoding="utf-8")
        print(f"💾 Đã lưu: {args.output_file}")

    return message_html


def _send_telegram_direct(html_text: str, settings) -> None:
    """Gửi thẳng qua Telegram adapter (dùng cho Telegraph mode)."""
    if not (settings.enable_telegram and settings.telegram_enabled):
        return
    from src.delivery.base import PlatformConfig
    from src.delivery.telegram import TelegramAdapter
    cfg = PlatformConfig(enabled=True, api_token=settings.telegram_token, chat_id=settings.chat_id)
    TelegramAdapter(cfg).deliver(html_text)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    setup_logging("ai-news")
    args = build_parser().parse_args()

    try:
        if args.show_state:
            cmd_show_state()
        elif args.reset_state:
            cmd_reset_state()
        elif args.test_source:
            cmd_test_source(args.test_source)
        elif args.dry_run or args.send:
            cmd_run(args)
        else:
            build_parser().print_help()
    except KeyboardInterrupt:
        print("\n⚠️  Đã dừng bởi người dùng.")
        sys.exit(0)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        print(f"❌ Pipeline thất bại: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
