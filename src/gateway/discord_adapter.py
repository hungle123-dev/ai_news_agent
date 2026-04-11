from __future__ import annotations

import logging
from typing import Optional

import requests

from src.gateway.base import BasePlatformAdapter, DeliveryResult, PlatformConfig

logger = logging.getLogger(__name__)


class DiscordAdapter(BasePlatformAdapter):
    platform_name = "discord"

    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self._webhook_url = config.api_token

    def connect(self) -> bool:
        if not self._webhook_url:
            self.logger.error("Discord webhook URL not configured")
            return False
        self._connected = True
        return True

    def send_html(self, html: str, **kwargs) -> DeliveryResult:
        if not self._webhook_url:
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error="Webhook URL not configured",
            )

        try:
            content = self._strip_html_for_discord(html)
            payload = {"content": content}
            response = requests.post(
                self._webhook_url,
                json=payload,
                timeout=self.config.timeout,
            )
            if response.status_code in (200, 204):
                return DeliveryResult(
                    success=True,
                    platform=self.platform_name,
                    message_id="discord_msg_sent",
                )
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error=f"HTTP {response.status_code}: {response.text[:100]}",
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
        self._connected = False

    def _strip_html_for_discord(self, html: str) -> str:
        import re
        content = html
        content = re.sub(r"<[^>]+>", "", content)
        content = content.replace("&nbsp;", " ")
        content = content.replace("&lt;", "<")
        content = content.replace("&gt;", ">")
        content = content.replace("&amp;", "&")
        return content.strip()[:2000]


__all__ = ["DiscordAdapter"]