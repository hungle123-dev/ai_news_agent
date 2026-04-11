"""
Gateway service - khởi tạo và cấu hình gateway dựa trên settings.
"""
from __future__ import annotations

import logging

from src.config import get_settings
from src.gateway.base import PlatformConfig
from src.gateway.discord_adapter import DiscordAdapter
from src.gateway.email_adapter import EmailAdapter, EmailConfig
from src.gateway.gateway import AINewsGateway
from src.gateway.telegram_adapter import TelegramAdapter

logger = logging.getLogger(__name__)


def build_gateway() -> AINewsGateway:
    """Build và configure gateway dựa trên settings."""
    settings = get_settings()
    gateway = AINewsGateway()

    if settings.enable_telegram and settings.telegram_enabled:
        telegram_config = PlatformConfig(
            enabled=True,
            api_token=settings.telegram_token,
            chat_id=settings.chat_id,
        )
        gateway.register_platform("telegram", TelegramAdapter(telegram_config))
        logger.info("Registered Telegram platform")

    if settings.enable_discord and settings.discord_enabled:
        discord_config = PlatformConfig(
            enabled=True,
            api_token=settings.discord_webhook_url,
        )
        gateway.register_platform("discord", DiscordAdapter(discord_config))
        logger.info("Registered Discord platform")

    if settings.enable_email and settings.email_enabled:
        email_config = EmailConfig(
            enabled=True,
            api_token=settings.email_username,
            smtp_host=settings.email_smtp_host or "",
            smtp_port=settings.email_smtp_port or 587,
            password=settings.email_password or "",
            from_email=settings.email_from or settings.email_username,
            to_email=settings.email_to or "",
        )
        gateway.register_platform("email", EmailAdapter(email_config))
        logger.info("Registered Email platform")

    return gateway


def get_active_platforms() -> list[str]:
    """Lấy danh sách platforms đang được bật."""
    settings = get_settings()
    platforms = []
    if settings.enable_telegram and settings.telegram_enabled:
        platforms.append("telegram")
    if settings.enable_discord and settings.discord_enabled:
        platforms.append("discord")
    if settings.enable_email and settings.email_enabled:
        platforms.append("email")
    return platforms


__all__ = ["build_gateway", "get_active_platforms"]