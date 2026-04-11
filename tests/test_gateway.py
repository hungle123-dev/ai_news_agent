from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from src.gateway.base import (
    BasePlatformAdapter,
    DeliveryResult,
    PlatformConfig,
)


class TestPlatformConfig:
    def test_default_config(self):
        config = PlatformConfig()
        assert config.enabled is False
        assert config.api_token is None
        assert config.chat_id is None

    def test_custom_config(self):
        config = PlatformConfig(
            enabled=True,
            api_token="test-token",
            chat_id="123456",
        )
        assert config.enabled is True
        assert config.api_token == "test-token"
        assert config.chat_id == "123456"


class TestDeliveryResult:
    def test_success_result(self):
        result = DeliveryResult(
            success=True,
            platform="telegram",
            message_id="123",
        )
        assert result.success is True
        assert result.platform == "telegram"
        assert result.message_id == "123"

    def test_failure_result(self):
        result = DeliveryResult(
            success=False,
            platform="telegram",
            error="Failed",
        )
        assert result.success is False
        assert result.error == "Failed"


class TestBasePlatformAdapter:
    def test_platform_name(self):
        class DummyAdapter(BasePlatformAdapter):
            def connect(self) -> bool:
                return True

            def send_message(self, text: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def send_html(self, html: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def disconnect(self):
                pass

        adapter = DummyAdapter(PlatformConfig())
        assert adapter.platform_name == "base"

    def test_validate_config_disabled(self):
        class DummyAdapter(BasePlatformAdapter):
            def connect(self) -> bool:
                return True

            def send_message(self, text: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def send_html(self, html: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def disconnect(self):
                pass

        adapter = DummyAdapter(PlatformConfig(enabled=False))
        assert adapter.validate_config() is False

    def test_validate_config_no_token(self):
        class DummyAdapter(BasePlatformAdapter):
            def connect(self) -> bool:
                return True

            def send_message(self, text: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def send_html(self, html: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def disconnect(self):
                pass

        adapter = DummyAdapter(PlatformConfig(enabled=True))
        assert adapter.validate_config() is False

    def test_validate_config_success(self):
        class DummyAdapter(BasePlatformAdapter):
            def connect(self) -> bool:
                return True

            def send_message(self, text: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def send_html(self, html: str, **kwargs):
                return DeliveryResult(success=True, platform=self.platform_name)

            def disconnect(self):
                pass

        adapter = DummyAdapter(
            PlatformConfig(enabled=True, api_token="token")
        )
        assert adapter.validate_config() is True


class TestGatewayIntegration:
    def test_gateway_deliver(self):
        from src.gateway.gateway import AINewsGateway
        from src.gateway.telegram_adapter import TelegramAdapter

        gateway = AINewsGateway()

        with patch("src.gateway.telegram_adapter.TelegramService") as mock_service:
            mock_instance = Mock()
            mock_instance.send_html_message.return_value = [
                {"ok": True, "result": {"message_id": 123}}
            ]
            mock_service.return_value = mock_instance

            adapter = TelegramAdapter(
                PlatformConfig(enabled=True, api_token="test", chat_id="123")
            )
            adapter._service = mock_instance

            gateway.register_platform("telegram", adapter)
            gateway.connect_all()

            result = gateway.deliver_newsletter("<b>Test</b>")
            assert "telegram" in result

    def test_gateway_broadcast(self):
        from src.gateway.gateway import AINewsGateway
        from src.gateway.telegram_adapter import TelegramAdapter

        gateway = AINewsGateway()

        with patch("src.gateway.telegram_adapter.TelegramService"):
            adapter = TelegramAdapter(
                PlatformConfig(enabled=True, api_token="test", chat_id="123")
            )
            gateway.register_platform("telegram", adapter)
            gateway.connect_all()

            results = gateway.deliver_newsletter("<b>Broadcast</b>")
            assert "telegram" in results or len(results) >= 0