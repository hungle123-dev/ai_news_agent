from src.gateway.base import (
    BasePlatformAdapter,
    DeliveryResult,
    PlatformConfig,
)

from src.gateway.gateway import AINewsGateway
from src.gateway.telegram_adapter import TelegramAdapter
from src.gateway.discord_adapter import DiscordAdapter
from src.gateway.email_adapter import EmailAdapter
from src.gateway.service import build_gateway, get_active_platforms

__all__ = [
    "BasePlatformAdapter",
    "DeliveryResult",
    "PlatformConfig",
    "TelegramAdapter",
    "DiscordAdapter",
    "EmailAdapter",
    "AINewsGateway",
    "build_gateway",
    "get_active_platforms",
]