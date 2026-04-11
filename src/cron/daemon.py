"""
Cron daemon for AI News Agent.
Run this script continuously to check and execute scheduled jobs.

Usage:
    python -m src.cron.daemon

Or run via Windows Task Scheduler to run every minute.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from src.cron.newsletter_scheduler import get_due_jobs
from src.cron.runner import run_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60  # Check every 60 seconds


def run_daemon():
    logger.info("Starting AI News cron daemon...")
    logger.info("Press Ctrl+C to stop")

    while True:
        try:
            due_jobs = get_due_jobs()
            if due_jobs:
                for job in due_jobs:
                    logger.info(f"Running due job: {job['id']} - {job.get('name', 'Unnamed')}")
                    try:
                        success = run_job(job['id'])
                        if success:
                            logger.info(f"Job {job['id']} completed successfully")
                        else:
                            logger.warning(f"Job {job['id']} did not run")
                    except Exception as e:
                        logger.exception(f"Job {job['id']} failed: {e}")
            else:
                logger.debug("No jobs due")
        except Exception as e:
            logger.exception(f"Error in daemon loop: {e}")

        time.sleep(CHECK_INTERVAL)


def run_once():
    """Run all due jobs once and exit. Use for Task Scheduler."""
    logger.info("Running due jobs once...")
    due_jobs = get_due_jobs()
    if not due_jobs:
        logger.info("No jobs due")
        return

    for job in due_jobs:
        logger.info(f"Running job: {job['id']}")
        try:
            success = run_job(job['id'])
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"Job {job['id']}: {status}")
        except Exception as e:
            logger.exception(f"Job {job['id']} failed: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        run_daemon()