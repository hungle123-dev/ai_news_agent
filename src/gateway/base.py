from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PlatformConfig:
    enabled: bool = False
    api_token: Optional[str] = None
    chat_id: Optional[str] = None
    retry_attempts: int = 3
    timeout: int = 30


@dataclass
class DeliveryResult:
    success: bool
    platform: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    attempt_count: int = 1


class BasePlatformAdapter(ABC):
    platform_name: str = "base"

    def __init__(self, config: PlatformConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.platform_name}")
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def send_message(self, text: str, **kwargs) -> DeliveryResult:
        pass

    @abstractmethod
    def send_html(self, html: str, **kwargs) -> DeliveryResult:
        pass

    @abstractmethod
    def disconnect(self):
        pass

    def validate_config(self) -> bool:
        if not self.config.enabled:
            self.logger.debug(f"{self.platform_name} is disabled")
            return False
        if not self.config.api_token:
            self.logger.error(f"{self.platform_name} missing API token")
            return False
        return True

    def deliver(self, html: str, **kwargs) -> DeliveryResult:
        if not self.validate_config():
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error="Configuration invalid or platform disabled",
            )

        try:
            result = self.send_html(html, **kwargs)
            self.logger.info(
                f"[{self.platform_name}] Delivery {'success' if result.success else 'failed'}: "
                f"{result.message_id or result.error}"
            )
            return result
        except Exception as e:
            self.logger.exception(f"[{self.platform_name}] Unexpected error")
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
            )


__all__ = [
    "BasePlatformAdapter",
    "DeliveryResult",
    "PlatformConfig",
]