"""
delivery/discord.py — Discord webhook adapter.
"""

from __future__ import annotations

import requests

from src.delivery.base import BasePlatformAdapter, DeliveryResult, PlatformConfig


class DiscordAdapter(BasePlatformAdapter):
    """Gửi newsletter qua Discord webhook."""
    platform_name = "discord"

    def connect(self) -> bool:
        return self.validate()

    def disconnect(self):
        pass

    def send_html(self, html_text: str, **kwargs) -> DeliveryResult:
        # Discord không hỗ trợ HTML — strip tags cơ bản
        import re
        plain = re.sub(r"<[^>]+>", "", html_text).strip()
        # Discord giới hạn 2000 ký tự mỗi message
        chunks = [plain[i:i + 1900] for i in range(0, len(plain), 1900)]

        webhook_url = self.config.api_token
        last_result = DeliveryResult(success=False, platform=self.platform_name)

        for chunk in chunks:
            try:
                resp = requests.post(webhook_url, json={"content": chunk}, timeout=30)
                resp.raise_for_status()
                last_result = DeliveryResult(success=True, platform=self.platform_name)
            except Exception as e:
                last_result = DeliveryResult(success=False, platform=self.platform_name, error=str(e))

        return last_result
