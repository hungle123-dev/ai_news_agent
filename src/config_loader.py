"""Config loader - parses config.yaml."""

from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent
CONFIG_FILE = _PROJECT_ROOT / "config.yaml"


def load_config() -> dict:
    """Load config.yaml."""
    if not CONFIG_FILE.exists():
        return {}

    text = CONFIG_FILE.read_text(encoding="utf-8")

    try:
        import yaml

        return yaml.safe_load(text) or {}
    except ImportError:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict:
    """Fallback parser if PyYAML not installed."""
    import re

    def parse_value(raw: str):
        raw = raw.strip()
        if raw.lower() in ("true", "yes"):
            return True
        if raw.lower() in ("false", "no"):
            return False
        if raw.lower() in ("null", "~", ""):
            return None
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if not inner:
                return []
            return [parse_value(x) for x in re.split(r",\s*", inner)]
        if raw.startswith(("'", '"')) and raw.endswith(raw[0]):
            return raw[1:-1]
        try:
            return int(raw)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass
        return raw

    root = {}
    stack = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        line = raw_line.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            item_str = line[2:].strip()
            if ":" in item_str and not item_str.startswith(("'", '"')):
                k, _, v = item_str.partition(":")
                d = {k.strip(): parse_value(v)}
                if isinstance(parent, list):
                    parent.append(d)
                stack.append((indent, d))
            else:
                if isinstance(parent, list):
                    parent.append(parse_value(item_str))
        elif ":" in line:
            k, _, v = line.partition(":")
            key = k.strip()
            v = v.strip()
            if not v:
                new = {}
                if isinstance(parent, dict):
                    parent[key] = new
                stack.append((indent, new))
            else:
                val = parse_value(v)
                if isinstance(parent, dict):
                    parent[key] = val
    return root


def get_source_config(source_name: str) -> dict:
    """Get config for a specific source."""
    cfg = load_config()
    sources = cfg.get("sources", {})
    return sources.get(source_name, {})


def is_source_enabled(source_name: str) -> bool:
    """Check if a source is enabled."""
    cfg = get_source_config(source_name)
    return cfg.get("enabled", True)


def get_source_keywords(source_name: str) -> list[str]:
    """Get keywords for a source."""
    cfg = get_source_config(source_name)
    return cfg.get("keywords", [])


def get_source_languages(source_name: str) -> list[str]:
    """Get languages for a source."""
    cfg = get_source_config(source_name)
    return cfg.get("languages", [])


def get_max_items(source_name: str) -> int:
    """Get max items for a source."""
    cfg = get_source_config(source_name)
    return cfg.get("max_items", 10)
