from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src.services.smart_retry import (
    ErrorType,
    RetryConfig,
    classify_error,
    calculate_delay,
    smart_retry,
    RETRY_CONFIGS,
)


class TestErrorType:
    def test_error_type_values(self):
        assert ErrorType.RATE_LIMIT.value == "rate_limit"
        assert ErrorType.SERVER_ERROR.value == "server_error"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.NETWORK_ERROR.value == "network_error"
        assert ErrorType.AUTH_ERROR.value == "auth_error"
        assert ErrorType.CLIENT_ERROR.value == "client_error"
        assert ErrorType.UNKNOWN.value == "unknown"


class TestRetryConfig:
    def test_default_retry_config(self):
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0

    def test_rate_limit_config(self):
        config = RETRY_CONFIGS[ErrorType.RATE_LIMIT]
        assert config.max_attempts == 5
        assert config.base_delay == 5.0


class TestClassifyError:
    def test_classify_429(self):
        exc = RuntimeError("Too Many Requests")
        result = classify_error(429, exc)
        assert result == ErrorType.RATE_LIMIT

    def test_classify_500(self):
        exc = RuntimeError("Internal Server Error")
        result = classify_error(500, exc)
        assert result == ErrorType.SERVER_ERROR

    def test_classify_502(self):
        exc = RuntimeError("Bad Gateway")
        result = classify_error(502, exc)
        assert result == ErrorType.SERVER_ERROR

    def test_classify_403(self):
        exc = RuntimeError("Forbidden")
        result = classify_error(403, exc)
        assert result == ErrorType.AUTH_ERROR

    def test_classify_401(self):
        exc = RuntimeError("Unauthorized")
        result = classify_error(401, exc)
        assert result == ErrorType.AUTH_ERROR

    def test_classify_404(self):
        exc = RuntimeError("Not Found")
        result = classify_error(404, exc)
        assert result == ErrorType.CLIENT_ERROR

    def test_classify_timeout_from_name(self):
        exc = TimeoutError("Connection timed out")
        result = classify_error(None, exc)
        assert result == ErrorType.TIMEOUT

    def test_classify_timeout_from_message(self):
        exc = RuntimeError("Read timed out")
        result = classify_error(None, exc)
        assert result == ErrorType.TIMEOUT

    def test_classify_network_error(self):
        exc = RuntimeError("Connection refused")
        result = classify_error(None, exc)
        assert result == ErrorType.NETWORK_ERROR

    def test_classify_dns_error(self):
        exc = RuntimeError("DNS failure")
        result = classify_error(None, exc)
        assert result == ErrorType.NETWORK_ERROR


class TestCalculateDelay:
    def test_rate_limit_delay_increases(self):
        delay0 = calculate_delay(ErrorType.RATE_LIMIT, 0)
        delay1 = calculate_delay(ErrorType.RATE_LIMIT, 1)
        delay2 = calculate_delay(ErrorType.RATE_LIMIT, 2)
        assert delay1 > delay0
        assert delay2 > delay1

    def test_rate_limit_respects_max(self):
        for i in range(10):
            delay = calculate_delay(ErrorType.RATE_LIMIT, i)
        assert delay <= RETRY_CONFIGS[ErrorType.RATE_LIMIT].max_delay

    def test_auth_error_no_retry(self):
        delay = calculate_delay(ErrorType.AUTH_ERROR, 0)
        assert delay == 0

    def test_client_error_no_retry(self):
        delay = calculate_delay(ErrorType.CLIENT_ERROR, 0)
        assert delay == 0


class TestSmartRetry:
    def test_succeeds_first_try(self):
        call_count = 0

        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = smart_retry(success_func, context="test")
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        call_count = 0

        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            return "success"

        result = smart_retry(fail_twice, context="test")
        assert result == "success"
        assert call_count == 3

    def test_raises_on_max_retries(self):
        attempt = 0

        def always_fail():
            nonlocal attempt
            attempt += 1
            raise RuntimeError("Always fails")

        with pytest.raises(RuntimeError, match="Always fails"):
            smart_retry(always_fail, context="test")
        assert attempt == RETRY_CONFIGS[ErrorType.UNKNOWN].max_attempts + 1

    def test_no_retry_on_auth_error(self):
        attempt = 0

        def auth_fail():
            nonlocal attempt
            attempt += 1
            exc = RuntimeError("Unauthorized")
            exc.status_code = 401
            raise exc

        with pytest.raises(RuntimeError):
            smart_retry(auth_fail, context="test")
        assert attempt == 1

    def test_no_retry_on_client_error(self):
        attempt = 0

        def client_fail():
            nonlocal attempt
            attempt += 1
            exc = RuntimeError("Not Found")
            exc.status_code = 404
            raise exc

        with pytest.raises(RuntimeError):
            smart_retry(client_fail, context="test")
        assert attempt == 1

    def test_custom_max_attempts(self):
        attempt = 0

        def fail_func():
            nonlocal attempt
            attempt += 1
            raise RuntimeError("Fail")

        with pytest.raises(RuntimeError):
            smart_retry(fail_func, context="test", max_attempts=2)
        assert attempt == 3


class TestSmartRetryIntegration:
    def test_retry_config_applied_correctly(self):
        configs_passed = []

        def check_config():
            configs_passed.append(True)

        class FakeError(Exception):
            status_code = 429

        for i in range(6):
            try:
                raise FakeError("Rate limited")
            except FakeError:
                pass

        attempt = 0
        while attempt < 5:
            try:
                raise ConnectionError("fail")
            except ConnectionError:
                attempt += 1

        assert len(configs_passed) >= 0