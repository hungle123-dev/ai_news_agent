# delivery package — gửi newsletter đến các platform
from .gateway import NewsGateway, build_gateway, get_active_platforms
from .base import BasePlatformAdapter, DeliveryResult, PlatformConfig
from .telegram import TelegramAdapter, render_newsletter_html, extract_message_html, publish_to_telegraph

__all__ = [
    "NewsGateway",
    "build_gateway",
    "get_active_platforms",
    "BasePlatformAdapter",
    "DeliveryResult",
    "PlatformConfig",
    "TelegramAdapter",
    "render_newsletter_html",
    "extract_message_html",
    "publish_to_telegraph",
]
