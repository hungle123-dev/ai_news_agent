from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.monitoring.usage_tracker import (
    MODEL_PRICING,
    UsageTracker,
    calculate_cost,
    get_tracker,
    get_report,
)


class TestCalculateCost:
    def test_gpt_4o_mini(self):
        cost = calculate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == 0.75

    def test_gpt_4o(self):
        cost = calculate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost == 12.5

    def test_unknown_model(self):
        cost = calculate_cost("unknown-model", 1_000_000, 1_000_000)
        assert cost == 5.0


class TestUsageTracker:
    @pytest.fixture
    def temp_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_tracker_creation(self, temp_storage):
        tracker = UsageTracker(storage_dir=temp_storage)
        assert tracker.storage_dir == temp_storage

    def test_record_request(self, temp_storage):
        tracker = UsageTracker(storage_dir=temp_storage)
        tracker.record_request(
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=100000,
            output_tokens=50000,
            success=True,
        )
        daily = tracker.get_daily_summary(1)
        assert daily["total_input_tokens"] == 100000
        assert daily["total_output_tokens"] == 50000

    def test_record_multiple_requests(self, temp_storage):
        tracker = UsageTracker(storage_dir=temp_storage)
        tracker.record_request(
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=100000,
            output_tokens=50000,
        )
        tracker.record_request(
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=200000,
            output_tokens=100000,
        )
        daily = tracker.get_daily_summary(1)
        assert daily["total_input_tokens"] == 300000
        assert daily["total_output_tokens"] == 150000

    def test_daily_summary_empty(self, temp_storage):
        tracker = UsageTracker(storage_dir=temp_storage)
        daily = tracker.get_daily_summary(7)
        assert daily["total_requests"] == 0

    def test_get_report(self, temp_storage):
        tracker = UsageTracker(storage_dir=temp_storage)
        tracker.record_request(
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        report = get_report()
        assert "Usage Report" in report


class TestGetTrackerSingleton:
    def test_singleton(self):
        with patch("src.monitoring.usage_tracker._tracker", None):
            with patch("src.monitoring.usage_tracker.Path.home") as mock_home:
                mock_home.return_value = Path(tempfile.gettempdir())
                tracker1 = get_tracker()
                tracker2 = get_tracker()
        assert tracker1 is tracker2