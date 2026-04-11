from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cron.runner import (
    advance_next_run,
    mark_job_run,
    run_job,
)


class TestAdvanceNextRun:
    def test_advances_cron_job(self, tmp_path):
        cron_dir = tmp_path / "cron"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        future_time = (datetime.now() + timedelta(days=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job",
                    "name": "Test Job",
                    "schedule": {"kind": "cron", "expr": "0 9 * * *"},
                    "enabled": True,
                    "next_run_at": future_time,
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                with patch("src.cron.newsletter_scheduler._compute_next_run") as mock_compute:
                    mock_compute.return_value = (
                        datetime.now() + timedelta(days=1)
                    ).isoformat()
                    from src.cron import runner
                    result = runner.advance_next_run("test-job")
        assert result is True

    def test_no_op_for_non_recurring(self, tmp_path):
        cron_dir = tmp_path / "cron"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job",
                    "name": "Test Job",
                    "schedule": {"kind": "once", "run_at": past_time},
                    "enabled": True,
                    "next_run_at": past_time,
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                from src.cron import runner
                result = runner.advance_next_run("test-job")
        assert result is False


class TestMarkJobRun:
    def test_mark_job_success(self, tmp_path):
        cron_dir = tmp_path / "cron_mark"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        future_time = (datetime.now() + timedelta(days=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job",
                    "name": "Test Job",
                    "schedule": {"kind": "cron", "expr": "0 9 * *"},
                    "enabled": True,
                    "next_run_at": future_time,
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                with patch(
                    "src.cron.newsletter_scheduler._compute_next_run"
                ) as mock_compute:
                    mock_compute.return_value = (
                        datetime.now() + timedelta(days=1)
                    ).isoformat()
                    from src.cron import runner
                    result = runner.mark_job_run("test-job", success=True)
        assert result["last_status"] == "success"

    def test_mark_job_failure(self, tmp_path):
        cron_dir = tmp_path / "cron_mark"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        future_time = (datetime.now() + timedelta(days=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job",
                    "name": "Test Job",
                    "schedule": {"kind": "cron", "expr": "0 9 * *"},
                    "enabled": True,
                    "next_run_at": future_time,
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                from src.cron import runner
                result = runner.mark_job_run(
                    "test-job", success=False, error="Test error"
                )
        assert result["last_status"] == "failed"
        assert result["last_error"] == "Test error"


class TestRunJob:
    def test_run_job_success(self, tmp_path):
        cron_dir = tmp_path / "cron_run"
        cron_dir.mkdir()
        jobs_file = cron_dir / "jobs.json"
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()
        jobs_data = {
            "jobs": [
                {
                    "id": "test-job",
                    "name": "Test Job",
                    "schedule": {"kind": "cron", "expr": "0 9 * *"},
                    "enabled": True,
                    "next_run_at": past_time,
                    "repo_limit": 5,
                    "paper_limit": 8,
                    "deliver": "telegram",
                }
            ]
        }
        jobs_file.write_text(json.dumps(jobs_data))
        with patch("src.cron.newsletter_scheduler.CRON_DIR", cron_dir):
            with patch("src.cron.newsletter_scheduler.JOBS_FILE", jobs_file):
                with patch(
                    "src.cron.newsletter_scheduler._compute_next_run"
                ) as mock_compute:
                    mock_compute.return_value = (
                        datetime.now() + timedelta(days=1)
                    ).isoformat()
                    from src.cron import runner
                    with patch.object(runner, "_execute_newsletter_job") as mock_exec:
                        mock_exec.return_value = "Success"
                        result = runner.run_job("test-job")
        assert result is True