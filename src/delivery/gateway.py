"""
delivery/gateway.py — Orchestrate gửi tin đến nhiều platform cùng lúc.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.delivery.base import BasePlatformAdapter, DeliveryResult

logger = logging.getLogger(__name__)


class NewsGateway:
    """Quản lý và phân phối newsletter đến nhiều platform."""

    def __init__(self):
        self._adapters: dict[str, BasePlatformAdapter] = {}

    def register(self, name: str, adapter: BasePlatformAdapter) -> None:
        self._adapters[name] = adapter

    def deliver(
        self,
        html: str,
        platforms: Optional[list[str]] = None,
        curated=None,
    ) -> dict[str, DeliveryResult]:
        """Gửi HTML đến các platform. Nếu platforms=None thì gửi tất cả."""
        targets = platforms or list(self._adapters.keys())
        results: dict[str, DeliveryResult] = {}

        for name in targets:
            adapter = self._adapters.get(name)
            if adapter is None:
                logger.warning("Platform '%s' chưa được đăng ký", name)
                continue
            results[name] = adapter.deliver(html, curated=curated)

        return results


# ── Factory ────────────────────────────────────────────────────────────────────

def build_gateway() -> NewsGateway:
    """Khởi tạo NewsGateway từ settings."""
    from src.settings import get_settings
    from src.delivery.base import PlatformConfig
    from src.delivery.telegram import TelegramAdapter
    from src.delivery.discord import DiscordAdapter
    from src.delivery.email import EmailAdapter, EmailConfig

    settings = get_settings()
    gateway = NewsGateway()

    if settings.enable_telegram and settings.telegram_enabled:
        cfg = PlatformConfig(
            enabled=True,
            api_token=settings.telegram_token,
            chat_id=settings.chat_id,
        )
        gateway.register("telegram", TelegramAdapter(cfg))
        logger.info("Registered: Telegram")

    if settings.enable_discord and settings.discord_enabled:
        cfg = PlatformConfig(enabled=True, api_token=settings.discord_webhook_url)
        gateway.register("discord", DiscordAdapter(cfg))
        logger.info("Registered: Discord")

    if settings.enable_email and settings.email_enabled:
        cfg = EmailConfig(
            enabled=True,
            api_token=settings.email_username,
            smtp_host=settings.email_smtp_host or "",
            smtp_port=settings.email_smtp_port,
            password=settings.email_password or "",
            from_email=settings.email_from or settings.email_username or "",
            to_email=settings.email_to or "",
        )
        gateway.register("email", EmailAdapter(cfg))
        logger.info("Registered: Email")

    return gateway


def get_active_platforms() -> list[str]:
    """Trả về danh sách các platform đang được bật."""
    from src.settings import get_settings
    settings = get_settings()
    platforms = []
    if settings.enable_telegram and settings.telegram_enabled:
        platforms.append("telegram")
    if settings.enable_discord and settings.discord_enabled:
        platforms.append("discord")
    if settings.enable_email and settings.email_enabled:
        platforms.append("email")
    return platforms
