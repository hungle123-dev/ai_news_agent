"""
state.py — Theo dõi các item đã xem để tránh gửi trùng.

Lưu danh sách URL đã seen vào ~/.ai-news/seen.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path.home() / ".ai-news"
STATE_FILE = STATE_DIR / "seen.json"

_DEFAULT_STATE = {"seen": [], "last_run": None}
_MAX_SEEN = 800  # Giữ tối đa 800 URL gần nhất


def load_state() -> dict:
    if not STATE_FILE.exists():
        return _DEFAULT_STATE.copy()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _DEFAULT_STATE.copy()


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def add_seen(urls: list[str]) -> dict:
    """Thêm URLs vào seen list, tự động cắt bớt nếu vượt _MAX_SEEN."""
    state = load_state()
    seen = list(dict.fromkeys(state.get("seen", []) + urls))[-_MAX_SEEN:]
    state["seen"] = seen
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return state


def is_seen(url: str) -> bool:
    return url.rstrip("/") in set(load_state().get("seen", []))


def get_stats() -> dict:
    state = load_state()
    return {"seen_count": len(state.get("seen", [])), "last_run": state.get("last_run")}


def clear_state() -> bool:
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        return True
    return False
