from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cron.newsletter_scheduler import (
    NewsletterJob,
    create_newsletter_job,
    ensure_dirs,
    get_due_jobs,
    list_jobs,
    load_jobs,
    parse_schedule,
    remove_job,
    save_jobs,
    trigger_job,
)


class TestParseSchedule:
    def test_parse_cron_expression(self):
        result = parse_schedule("0 9 * * *")
        assert result["kind"] == "cron"
        assert result["expr"] == "0 9 * * *"

    def test_parse_interval_recurring(self):
        result = parse_schedule("every 30m")
        assert result["kind"] == "interval"
        assert result["minutes"] == 30

    def test_parse_duration_once(self):
        result = parse_schedule("30m")
        assert result["kind"] == "once"

    def test_parse_duration_hours(self):
        result = parse_schedule("2h")
        assert result["kind"] == "once"
        assert result["minutes"] == 120

    def test_parse_duration_days(self):
        result = parse_schedule("1d")
        assert result["kind"] == "once"
        assert result["minutes"] == 1440

    def test_invalid_schedule_raises(self):
        with pytest.raises(ValueError):
            parse_schedule("invalid-schedule")


class TestEnsureDirs:
    def test_creates_directories(self, tmp_path):
        cron_dir = tmp_path / "cron"
        jobs_file = cron_dir / "jobs.json"
        ensure_dirs(cron_dir)
        assert cron_dir.exists()
        assert cron_dir.is_dir()


class TestJobCrud:
    @pytest.fixture
    def temp_storage(self, tmp_path):
        cron_dir = tmp_path / "cron"
        cron_dir.mkdir()
        return cron_dir

    @pytest.fixture
    def mock_ensure_dirs(self, temp_storage):
        with patch("src.cron.newsletter_scheduler.CRON_DIR", temp_storage):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", temp_storage / "jobs.json"):
                with patch("src.cron.newsletter_scheduler.OUTPUT_DIR", temp_storage / "output"):
                    ensure_dirs(temp_storage)
                    yield temp_storage

    def test_create_newsletter_job_cron(self, mock_ensure_dirs):
        job = create_newsletter_job(
            schedule="0 9 * * *",
            repo_limit=5,
            paper_limit=8,
            deliver="telegram",
        )
        assert job["name"] == "AI News Daily"
        assert job["schedule"]["kind"] == "cron"
        assert job["schedule"]["expr"] == "0 9 * * *"
        assert job["repo_limit"] == 5
        assert job["paper_limit"] == 8
        assert job["deliver"] == "telegram"
        assert job["enabled"] is True

    def test_create_newsletter_job_interval(self, mock_ensure_dirs):
        job = create_newsletter_job(
            schedule="every 30m",
            repo_limit=3,
            paper_limit=5,
            deliver="telegram",
        )
        assert job["schedule"]["kind"] == "interval"
        assert job["schedule"]["minutes"] == 30

    def test_list_jobs_empty(self, mock_ensure_dirs):
        jobs = list_jobs()
        assert jobs == []

    def test_list_jobs_with_data(self, mock_ensure_dirs):
        create_newsletter_job(
            schedule="0 9 * * *",
            repo_limit=5,
            paper_limit=8,
            deliver="telegram",
        )
        jobs = list_jobs()
        assert len(jobs) == 1

    def test_remove_job(self, mock_ensure_dirs):
        job = create_newsletter_job(
            schedule="0 9 * * *",
            repo_limit=5,
            paper_limit=8,
            deliver="telegram",
        )
        job_id = job["id"]
        removed = remove_job(job_id)
        assert removed is True
        jobs = list_jobs()
        assert len(jobs) == 0

    def test_remove_job_not_found(self, mock_ensure_dirs):
        removed = remove_job("nonexistent-id")
        assert removed is False

    def test_trigger_job(self, mock_ensure_dirs):
        job = create_newsletter_job(
            schedule="0 9 * * *",
            repo_limit=5,
            paper_limit=8,
            deliver="telegram",
        )
        job_id = job["id"]
        result = trigger_job(job_id)
        assert result is not None
        assert result["state"] == "scheduled"


class TestGetDueJobs:
    def test_get_due_jobs_none(self, tmp_path):
        cron_dir = tmp_path / "cron_none"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        jobs_file.write_text(json.dumps({"jobs": []}))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                with patch("src.cron.newsletter_scheduler.OUTPUT_DIR", cron_dir / "output"):
                    jobs = get_due_jobs()
                    assert jobs == []

    def test_get_due_jobs_with_past_run(self, tmp_path):
        cron_dir = tmp_path / "cron"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job-1",
                    "name": "Test Job",
                    "enabled": True,
                    "next_run_at": past_time,
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                with patch("src.cron.newsletter_scheduler.OUTPUT_DIR", cron_dir / "output"):
                    due = get_due_jobs()
                    assert len(due) == 1
                    assert due[0]["id"] == "test-job-1"

    def test_get_due_jobs_future_run(self, tmp_path):
        cron_dir = tmp_path / "cron"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        future_time = (datetime.now() + timedelta(hours=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job-1",
                    "name": "Test Job",
                    "enabled": True,
                    "next_run_at": future_time,
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                with patch("src.cron.newsletter_scheduler.OUTPUT_DIR", cron_dir / "output"):
                    due = get_due_jobs()
                    assert len(due) == 0

    def test_get_due_jobs_disabled(self, tmp_path):
        cron_dir = tmp_path / "cron"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job-1",
                    "name": "Test Job",
                    "enabled": False,
                    "next_run_at": past_time,
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                with patch("src.cron.newsletter_scheduler.OUTPUT_DIR", cron_dir / "output"):
                    due = get_due_jobs()
                    assert len(due) == 0