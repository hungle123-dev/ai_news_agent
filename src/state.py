"""State management - track seen items to avoid duplicates."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

STATE_DIR = Path.home() / ".ai-news"
STATE_FILE = STATE_DIR / "seen.json"


def load_state() -> dict:
    """Load state from seen.json."""
    if not STATE_FILE.exists():
        return {"seen": [], "last_run": None}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"seen": [], "last_run": None}


def save_state(state: dict) -> None:
    """Save state to seen.json."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_seen(urls: list[str], state: dict | None = None) -> dict:
    """Add URLs to seen list, keep max 800 items."""
    if state is None:
        state = load_state()

    seen_list = state.get("seen", [])
    seen_list.extend(urls)

    seen_list = list(dict.fromkeys(seen_list))[-800:]

    state["seen"] = seen_list
    state["last_run"] = datetime.now(timezone.utc).isoformat()

    save_state(state)
    return state


def is_seen(url: str, state: dict | None = None) -> bool:
    """Check if URL was already seen."""
    if state is None:
        state = load_state()
    return url.rstrip("/") in state.get("seen", [])


def filter_new(urls: list[str], state: dict | None = None) -> list[str]:
    """Filter out already seen URLs."""
    if state is None:
        state = load_state()
    seen_set = set(state.get("seen", []))

    new_urls = []
    for url in urls:
        if url.rstrip("/") not in seen_set:
            new_urls.append(url)

    return new_urls


def clear_state() -> bool:
    """Clear state file."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        return True
    return False


def get_stats(state: dict | None = None) -> dict:
    """Get state statistics."""
    if state is None:
        state = load_state()
    return {
        "seen_count": len(state.get("seen", [])),
        "last_run": state.get("last_run"),
    }
