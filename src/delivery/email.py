"""
delivery/email.py — Email adapter qua SMTP.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.delivery.base import BasePlatformAdapter, DeliveryResult, PlatformConfig


@dataclass
class EmailConfig(PlatformConfig):
    """Config mở rộng cho Email."""
    smtp_host: str = ""
    smtp_port: int = 587
    password: str = ""
    from_email: str = ""
    to_email: str = ""


class EmailAdapter(BasePlatformAdapter):
    """Gửi newsletter qua SMTP Email."""
    platform_name = "email"

    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.email_config: EmailConfig = config

    def connect(self) -> bool:
        return self.validate()

    def disconnect(self):
        pass

    def send_html(self, html_text: str, subject: str = "AI News", **kwargs) -> DeliveryResult:
        cfg = self.email_config
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = cfg.from_email or cfg.api_token or ""
            msg["To"] = cfg.to_email

            msg.attach(MIMEText(html_text, "html", "utf-8"))

            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(cfg.api_token or "", cfg.password)
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())

            return DeliveryResult(success=True, platform=self.platform_name)
        except Exception as e:
            return DeliveryResult(success=False, platform=self.platform_name, error=str(e))
