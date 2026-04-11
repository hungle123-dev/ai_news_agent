from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from src.gateway.base import BasePlatformAdapter, DeliveryResult, PlatformConfig

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig(PlatformConfig):
    smtp_host: str = ""
    smtp_port: int = 587
    password: str = ""
    from_email: str = ""
    to_email: str = ""


class EmailAdapter(BasePlatformAdapter):
    platform_name = "email"

    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self._smtp_host = getattr(config, "smtp_host", None)
        self._smtp_port = getattr(config, "smtp_port", 587)
        self._username = config.api_token
        self._password = getattr(config, "password", None)
        self._from_email = getattr(config, "from_email", None)
        self._to_email = getattr(config, "to_email", None)

    def connect(self) -> bool:
        if not all([self._smtp_host, self._username, self._password, self._to_email]):
            self.logger.error("Email config incomplete")
            return False
        try:
            server = smtplib.SMTP(self._smtp_host, self._smtp_port)
            server.starttls()
            server.login(self._username, self._password)
            server.quit()
            self._connected = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False

    def send_html(self, html: str, subject: str = "AI News", **kwargs) -> DeliveryResult:
        if not self._connected:
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error="Not connected. Call connect() first.",
            )

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from_email or self._username
            msg["To"] = self._to_email

            text_content = self._strip_html_for_text(html)
            html_part = MIMEText(html, "html")
            text_part = MIMEText(text_content, "plain")

            msg.attach(text_part)
            msg.attach(html_part)

            server = smtplib.SMTP(self._smtp_host, self._smtp_port)
            server.starttls()
            server.login(self._username, self._password)
            server.send_message(msg)
            server.quit()

            return DeliveryResult(
                success=True,
                platform=self.platform_name,
                message_id="email_sent",
            )
        except Exception as e:
            return DeliveryResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
            )

    def send_message(self, text: str, subject: str = "AI News", **kwargs) -> DeliveryResult:
        return self.send_html(f"<pre>{text}</pre>", subject=subject, **kwargs)

    def disconnect(self):
        self._connected = False

    def _strip_html_for_text(self, html: str) -> str:
        import re
        content = re.sub(r"<[^>]+>", "", html)
        content = content.replace("&nbsp;", " ")
        content = content.replace("&lt;", "<")
        content = content.replace("&gt;", ">")
        content = content.replace("&amp;", "&")
        return content.strip()


__all__ = ["EmailAdapter"]