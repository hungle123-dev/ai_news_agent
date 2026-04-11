from __future__ import annotations

import html
import re
import time
from urllib.parse import urlsplit

import requests

from src.config import get_settings
from src.models import CuratedNewsletter, NewsletterEntry
from telegraph import Telegraph


TELEGRAM_MESSAGE_LIMIT = 4000
HTML_TAG_RE = re.compile(r"(<[^>]+>)")
SELF_CLOSING_HTML_TAGS = {"br"}
ALLOWED_HTML_TAGS = {
    "a",
    "b",
    "blockquote",
    "code",
    "i",
    "pre",
    "s",
    "tg-spoiler",
    "u",
}


def normalize_telegram_html(message_html: str) -> str:
    message = message_html.strip()
    if message.startswith("```") and message.endswith("```"):
        lines = message.splitlines()
        if len(lines) >= 3:
            message = "\n".join(lines[1:-1]).strip()
    return sanitize_telegram_html(message)


def sanitize_telegram_html(message_html: str) -> str:
    sanitized = message_html.strip()
    sanitized = re.sub(r"<br\s*/?>", "\n", sanitized, flags=re.IGNORECASE)
    replacements = {
        "<strong>": "<b>",
        "</strong>": "</b>",
        "<em>": "<i>",
        "</em>": "</i>",
        "<ins>": "<u>",
        "</ins>": "</u>",
        "<strike>": "<s>",
        "</strike>": "</s>",
        "<del>": "<s>",
        "</del>": "</s>",
        "<ul>": "",
        "</ul>": "",
        "<ol>": "",
        "</ol>": "",
        "<li>": "• ",
        "</li>": "\n",
        "<p>": "",
        "</p>": "\n\n",
    }
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)

    def keep_supported_tags(match: re.Match[str]) -> str:
        tag = match.group(0)
        tag_name_match = re.match(r"</?\s*([a-zA-Z0-9-]+)", tag)
        if not tag_name_match:
            return ""
        name = tag_name_match.group(1).lower()
        if name in ALLOWED_HTML_TAGS:
            return tag
        return ""

    sanitized = HTML_TAG_RE.sub(keep_supported_tags, sanitized)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    return sanitized.strip()


def split_telegram_html_message(
    message_html: str,
    limit: int = TELEGRAM_MESSAGE_LIMIT,
) -> list[str]:
    normalized = normalize_telegram_html(message_html)
    if len(normalized) <= limit:
        return [normalized]

    tokens = [token for token in HTML_TAG_RE.split(normalized) if token]
    parts: list[str] = []
    current = ""
    open_tags: list[tuple[str, str]] = []

    def closing_tags(tags: list[tuple[str, str]]) -> str:
        return "".join(f"</{name}>" for name, _ in reversed(tags))

    def reopening_tags(tags: list[tuple[str, str]]) -> str:
        return "".join(raw_tag for _, raw_tag in tags)

    def visible_text(value: str) -> str:
        return HTML_TAG_RE.sub("", value).strip()

    def finalize_chunk() -> None:
        nonlocal current
        chunk = current + closing_tags(open_tags)
        if visible_text(chunk):
            parts.append(chunk)
        current = reopening_tags(open_tags)

    def tag_name(token: str) -> str | None:
        match = re.match(r"</?\s*([a-zA-Z0-9]+)", token)
        return match.group(1).lower() if match else None

    def is_closing_tag(token: str) -> bool:
        return token.startswith("</")

    def is_self_closing_tag(token: str) -> bool:
        name = tag_name(token)
        return token.endswith("/>") or name in SELF_CLOSING_HTML_TAGS

    for token in tokens:
        if token.startswith("<") and token.endswith(">"):
            name = tag_name(token)
            if not name:
                token = html.escape(token)
            else:
                future_tags = open_tags.copy()
                if is_closing_tag(token):
                    for idx in range(len(future_tags) - 1, -1, -1):
                        if future_tags[idx][0] == name:
                            future_tags.pop(idx)
                            break
                elif not is_self_closing_tag(token):
                    future_tags.append((name, token))

                if current and len(current) + len(token) + len(closing_tags(future_tags)) > limit:
                    finalize_chunk()

                current += token

                if is_closing_tag(token):
                    for idx in range(len(open_tags) - 1, -1, -1):
                        if open_tags[idx][0] == name:
                            open_tags.pop(idx)
                            break
                elif not is_self_closing_tag(token):
                    open_tags.append((name, token))
                continue

        remaining_text = token
        while remaining_text:
            remaining_space = limit - len(current) - len(closing_tags(open_tags))
            if remaining_space <= 0:
                finalize_chunk()
                remaining_space = limit - len(current) - len(closing_tags(open_tags))

            piece = remaining_text[:remaining_space]
            if len(piece) < len(remaining_text):
                split_at = max(piece.rfind("\n"), piece.rfind(" "))
                if split_at > 20:
                    piece = remaining_text[: split_at + 1]

            current += piece
            remaining_text = remaining_text[len(piece) :]
            if remaining_text:
                finalize_chunk()

    if visible_text(current + closing_tags(open_tags)):
        parts.append(current + closing_tags(open_tags))

    normalized_parts = [part for part in parts if visible_text(part)]
    if normalized_parts:
        return normalized_parts

    current = ""
    for paragraph in normalized.split("\n\n"):
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
            current = ""
        if len(paragraph) <= limit:
            current = paragraph
            continue
        for start in range(0, len(paragraph), limit):
            parts.append(paragraph[start : start + limit])
    if current:
        parts.append(current)
    return parts


def _safe_href(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return html.escape(url, quote=True)


def _render_entry(entry: NewsletterEntry, index: int) -> str:
    safe_title = html.escape(entry.title)
    safe_tldr = html.escape(entry.tldr)
    safe_why = html.escape(entry.why_it_matters)
    safe_href = _safe_href(entry.url)
    if safe_href:
        title_line = f"<b>{index}. <a href=\"{safe_href}\">{safe_title}</a></b>"
    else:
        title_line = f"<b>{index}. {safe_title}</b>"

    blocks = [
        title_line,
        safe_tldr,
        f"Vì sao đáng chú ý: {safe_why}",
    ]
    if entry.highlights:
        for highlight in entry.highlights:
            blocks.append(f"• {html.escape(highlight)}")
    if entry.source_signal:
        blocks.append(f"<i>{html.escape(entry.source_signal)}</i>")
    return "\n".join(blocks)


def render_curated_newsletter_html(curated: CuratedNewsletter) -> str:
    sections: list[str] = [f"<b>{html.escape(curated.headline)}</b>"]
    if curated.lead:
        sections.append(html.escape(curated.lead))

    if curated.repos:
        repo_block = ["<b>GitHub nổi bật</b>"]
        repo_block.extend(
            _render_entry(entry, index + 1) for index, entry in enumerate(curated.repos)
        )
        sections.append("\n\n".join(repo_block))

    if curated.papers:
        paper_block = ["<b>Paper nổi bật</b>"]
        paper_block.extend(
            _render_entry(entry, index + 1)
            for index, entry in enumerate(curated.papers)
        )
        sections.append("\n\n".join(paper_block))

    sections.append("<i>AI News Agent</i>")
    return "\n\n".join(sections)


_telegraph: Telegraph | None = None


def get_telegraph() -> Telegraph:
    global _telegraph
    if _telegraph is None:
        try:
            _telegraph = Telegraph()
            _telegraph.create_account(short_name="AINews")
        except Exception:
            _telegraph = Telegraph()
    return _telegraph


def convert_html_for_telegraph(html_content: str) -> str:
    import re
    
    content = html_content
    
    content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
    
    content = re.sub(r'\n\s*\n', '\n', content)
    
    content = re.sub(r'(<li[^>]*>.*?</li>)', r'\1\n', content, flags=re.DOTALL)
    
    content = re.sub(r'(<ul[^>]*>|</ul>)', r'\n\1\n', content, flags=re.IGNORECASE)
    content = re.sub(r'(<ol[^>]*>|</ol>)', r'\1\n', content, flags=re.IGNORECASE)
    
    content = re.sub(r'(<strong>([^<]+)</strong>)', r'<b>\2</b>', content)
    content = re.sub(r'(<em>([^<]+)</em>)', r'<i>\2</i>', content)
    
    content = re.sub(r'<u>([^<]+)</u>', r'<u>\1</u>', content)
    
    lines = content.split('\n')
    result_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('<ul') or line.startswith('<ol'):
            if not in_list:
                result_lines.append('')
                in_list = True
            result_lines.append(line)
        elif line.startswith('</ul>') or line.startswith('</ol>'):
            result_lines.append(line)
            result_lines.append('')
            in_list = False
        elif line.startswith('<li'):
            result_lines.append(line)
        else:
            if in_list:
                result_lines.append('')
                in_list = False
            result_lines.append(f'<p>{line}</p>')
    
    return '\n'.join(result_lines)


def publish_to_telegraph(
    title: str,
    html_content: str,
    author_name: str = "AI News Agent",
) -> str | None:
    telegraph_content = convert_html_for_telegraph(html_content)
    
    telegraph = get_telegraph()
    try:
        response = telegraph.create_page(
            title=title,
            html_content=telegraph_content,
            author_name=author_name,
        )
        return response.get("url")
    except Exception:
        return None


class TelegramService:
    def __init__(
        self,
        token: str | None = None,
        chat_id: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        settings = get_settings()
        self.token = token or settings.telegram_token
        self.chat_id = chat_id or settings.chat_id
        self.session = session

    def _require_credentials(self) -> None:
        if not self.token or not self.chat_id:
            raise RuntimeError(
                "Thiếu TELEGRAM_TOKEN hoặc CHAT_ID nên không thể gửi Telegram."
            )

    def _call_telegram_api(
        self,
        endpoint: str,
        payload: dict,
        *,
        use_get: bool = False,
    ) -> dict:
        session = self.session or requests.Session()
        request_kwargs = {
            "timeout": 30,
            "headers": {
                "Connection": "close",
                "User-Agent": "ai-news-agent/1.0",
            },
        }

        if use_get:
            response = session.get(endpoint, params=payload, **request_kwargs)
        else:
            response = session.post(endpoint, json=payload, **request_kwargs)

        try:
            result = response.json()
        except ValueError:
            result = {"ok": False, "description": response.text}

        if response.status_code >= 400 or not result.get("ok"):
            description = result.get("description") or result
            raise RuntimeError(
                f"Telegram API lỗi {response.status_code}: {description}"
            )
        return result

    def send_html_message(
        self,
        message_html: str,
        disable_web_page_preview: bool = True,
    ) -> list[dict]:
        self._require_credentials()
        endpoint = f"https://api.telegram.org/bot{self.token}/sendMessage"
        normalized_message = sanitize_telegram_html(message_html)

        responses: list[dict] = []
        for chunk in split_telegram_html_message(normalized_message):
            payload = {
                "chat_id": self.chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_web_page_preview,
            }

            last_error: Exception | None = None
            for attempt in range(4):
                try:
                    responses.append(self._call_telegram_api(endpoint, payload, use_get=False))
                    last_error = None
                    break
                except RuntimeError as exc:
                    last_error = exc
                    if "Telegram API lỗi 4" in str(exc):
                        break
                    if attempt < 3:
                        time.sleep(1.5 * (attempt + 1))
                except requests.RequestException as exc:
                    last_error = exc
                    if attempt < 3:
                        time.sleep(1.5 * (attempt + 1))

            if last_error is not None and isinstance(last_error, requests.RequestException):
                for attempt in range(2):
                    try:
                        responses.append(
                            self._call_telegram_api(endpoint, payload, use_get=True)
                        )
                        last_error = None
                        break
                    except (requests.RequestException, RuntimeError) as exc:
                        last_error = exc
                        if attempt < 1:
                            time.sleep(2 * (attempt + 1))

            if last_error is not None:
                raise last_error

        return responses

    def send_via_telegraph(
        self,
        title: str,
        html_content: str,
        preview_text: str | None = None,
    ) -> dict | None:
        telegraph_url = publish_to_telegraph(title, html_content)
        if not telegraph_url:
            return None

        preview = preview_text or f"<b>{title}</b>\n\n👉 <a href='{telegraph_url}'>Đọc chi tiết (Instant View)</a>"
        try:
            return self._call_telegram_api(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                {
                    "chat_id": self.chat_id,
                    "text": preview,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                use_get=False,
            )
        except Exception:
            return None


__all__ = [
    "TELEGRAM_MESSAGE_LIMIT",
    "TelegramService",
    "normalize_telegram_html",
    "sanitize_telegram_html",
    "render_curated_newsletter_html",
    "split_telegram_html_message",
    "publish_to_telegraph",
    "send_system_alert",
]


def send_system_alert(message: str) -> bool:
    """Gửi tin nhắn cảnh báo kỹ thuật/chi phí lên Telegram Admin"""
    try:
        service = TelegramService()
        alert_html = f"🚨 <b>CẢNH BÁO HỆ THỐNG AI NEWS</b> 🚨\n\n{message}"
        service.send_html_message(alert_html)
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Cannot send alert to Telegram: {e}")
        return False


def send_quota_alert(alert_type: str, details: str) -> bool:
    """Gửi cảnh báo liên quan đến quota/credit"""
    if alert_type == "quota_exceeded":
        message = (
            f"💸 <b>TÀI KHOẢN API LLM ĐÃ HẾT TIỀN!</b>\n\n"
            f"Chi tiết: <code>{details[:200]}</code>\n\n"
            "Vui lòng nạp thêm credit để hệ thống tiếp tục hoạt động."
        )
    elif alert_type == "budget_80":
        message = (
            f"⚠️ <b>SẮP HẾT NGÂN SÁCH</b>\n\n"
            f"Đã dùng <b>{details}</b> trong tháng này.\n"
            "Nếu tiếp tục sử dụng với tốc độ hiện tại, có thể hết credit trong tháng."
        )
    elif alert_type == "budget_100":
        message = (
            f"⚠️ <b>ĐÃ CHẠM NGƯỠNG CHI PHÍ</b>\n\n"
            f"Đã dùng <b>{details}</b> - vượt hạn mức ngân sách tháng."
        )
    else:
        message = details
    
    return send_system_alert(message)
