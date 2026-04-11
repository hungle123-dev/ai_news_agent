from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Callable, TypeVar, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorType(Enum):
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    AUTH_ERROR = "auth_error"
    CLIENT_ERROR = "client_error"
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


RETRY_CONFIGS: dict[ErrorType, RetryConfig] = {
    ErrorType.QUOTA_EXCEEDED: RetryConfig(max_attempts=0),
    ErrorType.RATE_LIMIT: RetryConfig(
        max_attempts=5,
        base_delay=5.0,
        max_delay=300.0,
        exponential_base=1.5,
    ),
    ErrorType.SERVER_ERROR: RetryConfig(
        max_attempts=4,
        base_delay=2.0,
        max_delay=60.0,
        exponential_base=2.0,
    ),
    ErrorType.TIMEOUT: RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
    ),
    ErrorType.NETWORK_ERROR: RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
    ),
    ErrorType.AUTH_ERROR: RetryConfig(max_attempts=0),
    ErrorType.CLIENT_ERROR: RetryConfig(max_attempts=0),
    ErrorType.UNKNOWN: RetryConfig(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0,
    ),
}


def classify_error(status_code: Optional[int] | None, exception: Exception) -> ErrorType:
    if status_code:
        if status_code == 429:
            return ErrorType.RATE_LIMIT
        if status_code in (500, 502, 503, 504):
            return ErrorType.SERVER_ERROR
        if status_code in (401, 403):
            return ErrorType.AUTH_ERROR
        if 400 <= status_code < 500:
            return ErrorType.CLIENT_ERROR

    exc_name = type(exception).__name__
    exc_msg = str(exception).lower()

    if any(kw in exc_msg for kw in ["quota", "insufficient", "balance", "credit", "exceeded your current quota", "out ofcredit", "out of credit"]):
        return ErrorType.QUOTA_EXCEEDED
    if "timeout" in exc_name.lower() or "timed out" in exc_msg:
        return ErrorType.TIMEOUT
    if any(
        kw in exc_msg
        for kw in ["connection", "network", "dns", "refused", "reset"]
    ):
        return ErrorType.NETWORK_ERROR
    if "auth" in exc_msg or "unauthorized" in exc_msg:
        return ErrorType.AUTH_ERROR

    return ErrorType.UNKNOWN


def calculate_delay(error_type: ErrorType, attempt: int) -> float:
    config = RETRY_CONFIGS[error_type]
    if config.max_attempts == 0:
        return 0
    delay = config.base_delay * (config.exponential_base**attempt)
    return min(delay, config.max_delay)


def smart_retry(
    func: Callable[[], T],
    context: str = "operation",
    max_attempts: Optional[int] = None,
) -> T:
    attempt = 0
    last_error: Optional[Exception] = None

    while True:
        try:
            return func()
        except Exception as e:
            last_error = e
            status_code = getattr(e, "status_code", None)
            error_type = classify_error(status_code, e)
            config = RETRY_CONFIGS[error_type]

            if max_attempts is not None:
                config.max_attempts = max_attempts

            if attempt >= config.max_attempts:
                logger.error(
                    f"[{context}] Max retries ({config.max_attempts}) reached. "
                    f"Error type: {error_type.value}, Last error: {e}"
                )
                raise

            if config.max_attempts == 0:
                logger.warning(
                    f"[{context}] Non-retryable error: {error_type.value}"
                )
                raise

            delay = calculate_delay(error_type, attempt)
            logger.warning(
                f"[{context}] Attempt {attempt + 1} failed: {error_type.value}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            attempt += 1


__all__ = [
    "ErrorType",
    "RetryConfig",
    "RETRY_CONFIGS",
    "classify_error",
    "calculate_delay",
    "smart_retry",
]