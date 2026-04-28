"""
delivery/telegram.py — Telegram adapter, service và Telegraph publisher.

Gồm 3 phần:
  1. TelegramAdapter   — BasePlatformAdapter gửi HTML qua Bot API
  2. render_*          — Hàm render CuratedNewsletter → HTML
  3. Telegraph         — Publish bài dài lên Telegraph
"""

from __future__ import annotations

import html
import logging
import re
from typing import Optional

import requests

from src.delivery.base import BasePlatformAdapter, DeliveryResult
from src.models import CuratedNewsletter, FormattedNewsletter

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
_MAX_MSG_LEN = 4096


# ── HTML Utilities ─────────────────────────────────────────────────────────────

_ALLOWED_TAGS = re.compile(
    r"<(?!/?(?:b|i|u|s|code|pre|a(?:\s+href=['\"][^'\"]*['\"])?|br)\b)[^>]+>",
    re.IGNORECASE,
)


def normalize_telegram_html(text: str) -> str:
    """Giữ lại các thẻ HTML Telegram hỗ trợ, loại bỏ phần còn lại."""
    text = _ALLOWED_TAGS.sub("", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    return text.strip()


# ── Rendering CuratedNewsletter → HTML ────────────────────────────────────────

def render_newsletter_html(newsletter: CuratedNewsletter) -> str:
    """Render CuratedNewsletter thành HTML cho Telegram."""
    parts: list[str] = []

    # Header
    parts.append(f"<b>🗞 {html.escape(newsletter.headline)}</b>")
    if newsletter.lead:
        parts.append(html.escape(newsletter.lead))

    # GitHub Repos
    if newsletter.repos:
        parts.append("\n<b>🔥 GitHub Trending</b>")
        for entry in newsletter.repos:
            block = [f'• <a href="{entry.url}">{html.escape(entry.title)}</a>']
            block.append(f"  <i>{html.escape(entry.tldr)}</i>")
            if entry.why_it_matters:
                block.append(f"  💡 {html.escape(entry.why_it_matters)}")
            for h_item in entry.highlights:
                block.append(f"    – {html.escape(h_item)}")
            parts.append("\n".join(block))

    # Articles
    if newsletter.articles:
        parts.append("\n<b>📰 Tin tức</b>")
        for entry in newsletter.articles:
            block = [f'• <a href="{entry.url}">{html.escape(entry.title)}</a>']
            block.append(f"  <i>{html.escape(entry.tldr)}</i>")
            if entry.why_it_matters:
                block.append(f"  💡 {html.escape(entry.why_it_matters)}")
            parts.append("\n".join(block))

    parts.append("\n<i>AI News Agent</i>")
    return "\n\n".join(parts)


# ── Extract HTML từ CrewOutput ─────────────────────────────────────────────────

def extract_message_html(crew_output) -> str:
    """
    Lấy HTML cuối cùng từ CrewAI output.
    Ưu tiên FormattedNewsletter, fallback sang CuratedNewsletter, raw text.
    """
    # Kiểm tra output chính
    if isinstance(crew_output.pydantic, FormattedNewsletter):
        body = normalize_telegram_html(crew_output.pydantic.message_html)
        title = crew_output.pydantic.title.strip()
        return f"<b>{html.escape(title)}</b>\n\n{body}" if title and title not in body else body

    # Kiểm tra từng task output (theo thứ tự ngược)
    for task_output in reversed(crew_output.tasks_output or []):
        if isinstance(task_output.pydantic, FormattedNewsletter):
            body = normalize_telegram_html(task_output.pydantic.message_html)
            title = task_output.pydantic.title.strip()
            return f"<b>{html.escape(title)}</b>\n\n{body}" if title and title not in body else body
        if isinstance(task_output.pydantic, CuratedNewsletter):
            return render_newsletter_html(task_output.pydantic)

    return normalize_telegram_html(crew_output.raw)


# ── TelegramAdapter ───────────────────────────────────────────────────────────

class TelegramAdapter(BasePlatformAdapter):
    """Gửi HTML message qua Telegram Bot API."""
    platform_name = "telegram"

    def connect(self) -> bool:
        return self.validate()

    def disconnect(self):
        pass

    def send_html(self, html_text: str, **kwargs) -> DeliveryResult:
        return self._send(html_text)

    def _send(self, text: str) -> DeliveryResult:
        token = self.config.api_token
        chat_id = self.config.chat_id

        # Chia nhỏ nếu quá dài
        chunks = _split_html(text, _MAX_MSG_LEN)
        last_result = DeliveryResult(success=False, platform=self.platform_name)

        for chunk in chunks:
            url = _TELEGRAM_API.format(token=token, method="sendMessage")
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            try:
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                msg_id = str(data.get("result", {}).get("message_id", ""))
                last_result = DeliveryResult(success=True, platform=self.platform_name, message_id=msg_id)
            except Exception as e:
                last_result = DeliveryResult(success=False, platform=self.platform_name, error=str(e))

        return last_result


def _split_html(text: str, max_len: int) -> list[str]:
    """Chia text thành các đoạn ≤ max_len ký tự, cắt tại newline."""
    if len(text) <= max_len:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current.strip())
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current.strip())
    return chunks


# ── Telegraph ─────────────────────────────────────────────────────────────────

def render_telegraph_html(curated: CuratedNewsletter) -> str:
    """Render HTML chuẩn dành riêng cho bài viết Telegraph (hỗ trợ p, br, h3, ul, li)."""
    parts = []
    
    if curated.lead:
        parts.append(f"<p><em>{html.escape(curated.lead)}</em></p>")
        parts.append("<hr>")
        
    if curated.repos:
        parts.append("<h3>🔥 GitHub Trending</h3>")
        parts.append("<ul>")
        for r in curated.repos:
            parts.append("<li>")
            parts.append(f"<strong><a href=\"{r.url}\">{html.escape(r.title)}</a></strong><br>")
            parts.append(f"{html.escape(r.tldr)}<br>")
            parts.append(f"💡 <em>Góc nhìn Dev:</em> {html.escape(r.why_it_matters)}")
            if r.highlights:
                parts.append("<ul>")
                for h in r.highlights:
                    parts.append(f"<li>{html.escape(h)}</li>")
                parts.append("</ul>")
            parts.append("</li><br>")
        parts.append("</ul>")
        parts.append("<hr>")
        
    if curated.articles:
        parts.append("<h3>📰 Tin tức nổi bật</h3>")
        parts.append("<ul>")
        for a in curated.articles:
            parts.append("<li>")
            parts.append(f"<strong><a href=\"{a.url}\">{html.escape(a.title)}</a></strong><br>")
            parts.append(f"{html.escape(a.tldr)}<br>")
            parts.append(f"💡 <em>Tại sao quan trọng:</em> {html.escape(a.why_it_matters)}")
            parts.append("</li><br>")
        parts.append("</ul>")
        parts.append("<hr>")
        
    parts.append("<p><em>Bản tin được tổng hợp tự động bởi AI News Agent.</em></p>")
    return "".join(parts)


def publish_to_telegraph(
    title: str,
    html_content: Optional[str] = None,
    curated: Optional[CuratedNewsletter] = None,
) -> Optional[str]:
    """
    Publish bài dài lên Telegraph, trả về URL.
    Sử dụng render_telegraph_html nếu có CuratedNewsletter.
    """
    if curated is not None:
        final_html = render_telegraph_html(curated)
    elif html_content is not None:
        final_html = html_content.replace("\n", "<br>")
    else:
        return None

    try:
        from telegraph import Telegraph
        tg = Telegraph()
        tg.create_account(short_name="ai-news-agent")
        response = tg.create_page(title=title, html_content=final_html)
        return f"https://telegra.ph/{response['path']}"
    except Exception as e:
        logger.error("Telegraph publish failed: %s", e)
        return None
