"""
delivery/base.py — Abstract base cho tất cả platform adapters.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_CHAT_ID_RE = re.compile(r"^-?\d+$")


@dataclass
class PlatformConfig:
    """Cấu hình cho một platform gửi tin."""
    enabled: bool = False
    api_token: Optional[str] = None
    chat_id: Optional[str] = None
    retry_attempts: int = 3
    timeout: int = 30

    def __post_init__(self):
        if self.chat_id and not _CHAT_ID_RE.match(self.chat_id):
            raise ValueError(f"chat_id không hợp lệ: {self.chat_id!r} (phải là số nguyên)")


@dataclass
class DeliveryResult:
    """Kết quả gửi tin cho một platform."""
    success: bool
    platform: str
    message_id: Optional[str] = None
    error: Optional[str] = None


class BasePlatformAdapter(ABC):
    """Base class cho mọi platform adapter (Telegram, Discord, Email...)."""
    platform_name: str = "base"

    def __init__(self, config: PlatformConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.platform_name}")

    # Mỗi subclass phải implement 3 method này
    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def send_html(self, html: str, **kwargs) -> DeliveryResult: ...

    @abstractmethod
    def disconnect(self): ...

    def validate(self) -> bool:
        """Kiểm tra config có đủ thông tin để gửi không."""
        if not self.config.enabled:
            return False
        if not self.config.api_token:
            self.logger.error("%s: thiếu API token", self.platform_name)
            return False
        return True

    def deliver(self, html: str, **kwargs) -> DeliveryResult:
        """Template method: validate → send_html, bắt exception."""
        if not self.validate():
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error="Config không hợp lệ hoặc platform bị tắt",
            )
        try:
            result = self.send_html(html, **kwargs)
            self.logger.info("[%s] %s: %s",
                             self.platform_name,
                             "OK" if result.success else "FAIL",
                             result.message_id or result.error)
            return result
        except Exception as e:
            self.logger.exception("[%s] Lỗi không mong muốn", self.platform_name)
            return DeliveryResult(success=False, platform=self.platform_name, error=str(e))
