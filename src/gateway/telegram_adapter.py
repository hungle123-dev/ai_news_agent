from __future__ import annotations

from typing import Optional

from src.gateway.base import BasePlatformAdapter, DeliveryResult, PlatformConfig
from src.services.telegram_service import TelegramService


class TelegramAdapter(BasePlatformAdapter):
    platform_name = "telegram"

    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self._service: Optional[TelegramService] = None

    def connect(self) -> bool:
        try:
            self._service = TelegramService(
                token=self.config.api_token,
                chat_id=self.config.chat_id,
            )
            self._connected = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False

    def send_html(self, html: str, **kwargs) -> DeliveryResult:
        if not self._service:
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error="Not connected. Call connect() first.",
            )

        try:
            responses = self._service.send_html_message(html)
            message_id = (
                responses[0].get("result", {}).get("message_id")
                if responses else None
            )
            return DeliveryResult(
                success=True,
                platform=self.platform_name,
                message_id=str(message_id) if message_id else None,
            )
        except Exception as e:
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
            )

    def send_message(self, text: str, **kwargs) -> DeliveryResult:
        return self.send_html(f"<pre>{text}</pre>", **kwargs)

    def disconnect(self):
        self._service = None
        self._connected = False


__all__ = ["TelegramAdapter"]