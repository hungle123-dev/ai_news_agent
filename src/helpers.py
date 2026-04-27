"""
Utility functions for AI News Agent.
Shared helper functions used across modules.
"""
from __future__ import annotations

import html

from src.models import CuratedNewsletter, FormattedNewsletter
from src.services.telegram_service import (
    normalize_telegram_html,
    render_curated_newsletter_html,
)


def extract_message_html(crew_output) -> str:
    """Extract HTML message from crew output.
    
    Handles both FormattedNewsletter and CuratedNewsletter formats.
    """
    if isinstance(crew_output.pydantic, FormattedNewsletter):
        body = normalize_telegram_html(crew_output.pydantic.message_html)
        title = crew_output.pydantic.title.strip()
        if title and title not in body:
            return f"<b>{html.escape(title)}</b><br><br>{body}"
        return body

    for task_output in reversed(crew_output.tasks_output or []):
        if isinstance(task_output.pydantic, FormattedNewsletter):
            body = normalize_telegram_html(task_output.pydantic.message_html)
            title = task_output.pydantic.title.strip()
            if title and title not in body:
                return f"<b>{html.escape(title)}</b><br><br>{body}"
            return body
        if isinstance(task_output.pydantic, CuratedNewsletter):
            return render_curated_newsletter_html(task_output.pydantic)

    return normalize_telegram_html(crew_output.raw)


__all__ = ["extract_message_html"]