from __future__ import annotations

from typing import Optional

from src.gateway.base import (
    BasePlatformAdapter,
    DeliveryResult,
    PlatformConfig,
)


class AINewsGateway:
    def __init__(self):
        self._platforms: dict[str, BasePlatformAdapter] = {}

    def register_platform(self, name: str, adapter: BasePlatformAdapter):
        self._platforms[name] = adapter

    def connect_all(self):
        for name, adapter in self._platforms.items():
            if adapter.config.enabled:
                adapter.connect()

    def deliver_newsletter(
        self,
        html: str,
        platforms: Optional[list[str]] = None,
    ) -> dict[str, DeliveryResult]:
        targets = platforms or list(self._platforms.keys())
        results = {}
        for name in targets:
            adapter = self._platforms.get(name)
            if adapter and adapter.config.enabled:
                results[name] = adapter.deliver(html)
            elif adapter:
                results[name] = DeliveryResult(
                    success=False,
                    platform=name,
                    error="Platform disabled",
                )
        return results

    def disconnect_all(self):
        for adapter in self._platforms.values():
            adapter.disconnect()


__all__ = ["AINewsGateway"]