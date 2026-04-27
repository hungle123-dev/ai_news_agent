"""File logging setup for AI News Agent."""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path.home() / ".ai-news"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "radar.log"


def setup_logging(name: str = "ai-news") -> logging.Logger:
    """Setup file logging + console logging."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log(message: str, level: str = "INFO") -> None:
    """Quick log helper."""
    logger = logging.getLogger("ai-news")
    if not logger.handlers:
        logger = setup_logging()

    getattr(logger, level.lower(), logger.info)(message)


setup_logging()

INFO = lambda msg: log(msg, "INFO")
WARNING = lambda msg: log(msg, "WARNING")
ERROR = lambda msg: log(msg, "ERROR")
