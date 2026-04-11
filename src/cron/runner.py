from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.cron.newsletter_scheduler import (
    load_jobs,
    save_jobs,
    _compute_next_run,
)
from src.services.telegram_service import send_quota_alert
from src.utils import extract_message_html

logger = logging.getLogger(__name__)


def advance_next_run(job_id: str) -> bool:
    jobs = load_jobs()
    for job in jobs:
        if job["id"] != job_id:
            continue

        schedule = job.get("schedule", {})
        kind = schedule.get("kind")

        if kind not in ("cron", "interval"):
            return False

        new_next = _compute_next_run(schedule)

        if new_next and new_next != job.get("next_run_at"):
            job["next_run_at"] = new_next
            save_jobs(jobs)
            logger.info(f"Job {job_id}: advanced next_run to {new_next}")
            return True

        return False

    return False


def mark_job_run(
    job_id: str,
    success: bool,
    error: Optional[str] = None,
) -> Optional[dict]:
    jobs = load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            job["last_run_at"] = datetime.now().isoformat()
            job["last_status"] = "success" if success else "failed"
            job["last_error"] = error
            
            schedule = job.get("schedule", {})
            repeat = job.get("repeat", {})
            schedule_kind = schedule.get("kind")
            
            if success and "completed" in repeat:
                repeat["completed"] += 1
            
            if schedule_kind in ("cron", "interval"):
                job["next_run_at"] = _compute_next_run(schedule)
            elif schedule_kind == "once" or schedule_kind is None:
                job["enabled"] = False
                job["next_run_at"] = None
                
            times_to_run = repeat.get("times", 1)
            completed_times = repeat.get("completed", 0)
            if times_to_run and completed_times >= times_to_run:
                job["enabled"] = False
                job["next_run_at"] = None
                    
            job["state"] = "completed"
            save_jobs(jobs)
            return job
    return None


def run_job(job_id: str) -> bool:
    jobs = load_jobs()
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        logger.error(f"Job {job_id} not found")
        return False

    if not job.get("enabled", True):
        logger.info(f"Job {job_id}: disabled, skipping")
        return False

    schedule = job.get("schedule", {})
    repeat = job.get("repeat", {})

    if schedule.get("kind") == "once":
        if job.get("last_status") == "success":
            job["enabled"] = False
            save_jobs(jobs)
            logger.info(f"Job {job_id}: already completed (once job), skipping")
            return False

    advanced = advance_next_run(job_id)

    if not advanced and schedule.get("kind") != "once":
        logger.info(f"Job {job_id}: skipping (not a recurring job or already advanced)")
        return False

    try:
        result = _execute_newsletter_job(job_id)
        mark_job_run(job_id, success=True)
        logger.info(f"Job {job_id}: completed successfully")
        return True

    except Exception as e:
        logger.exception(f"Job {job_id}: failed with error")
        
        error_str = str(e).lower()
        if any(kw in error_str for kw in ["insufficient_quota", "exceeded your current quota", "out of credit", "quota", "balance", "exceeded"]):
            send_quota_alert("quota_exceeded", error_str)
        
        mark_job_run(job_id, success=False, error=str(e))
        return False


def _execute_newsletter_job(job_id: str) -> str:
    from src.crew import AINewsCrew
    from src.config import get_settings
    from src.gateway.service import build_gateway, get_active_platforms
    from src.memory.newsletter_memory import (
        NewsletterHistory,
        get_memory,
    )
    from src.monitoring import record_pipeline_run

    jobs = load_jobs()
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    settings = get_settings()
    repo_limit = job.get("repo_limit", 5)
    paper_limit = job.get("paper_limit", 8)

    crew = AINewsCrew(repo_limit=repo_limit, paper_limit=paper_limit)
    crew_output = crew.crew().kickoff()

    message_html = extract_message_html(crew_output)

    active_platforms = get_active_platforms()
    success = False
    
    if active_platforms:
        gateway = build_gateway()
        gateway.connect_all()
        results = gateway.deliver_newsletter(
            message_html,
            platforms=active_platforms
        )
        success = any(r.success for r in results.values())
    else:
        logger.warning("No active platforms configured")

    memory = get_memory()
    memory.add_to_history(
        NewsletterHistory(
            date=datetime.now().isoformat(),
            headline=crew_output.pydantic.title if hasattr(crew_output.pydantic, 'title') else "AI News",
            repo_count=repo_limit,
            paper_count=paper_limit,
            delivery_status="success" if success else "failed",
            delivery_platforms=active_platforms if active_platforms else [],
        )
    )
    
    record_pipeline_run(
        model=settings.openai_model if settings.llm_provider == "openai" else settings.gemini_model,
        provider=settings.llm_provider,
        repo_count=repo_limit,
        paper_count=paper_limit,
        success=success,
    )

    return message_html


__all__ = [
    "advance_next_run",
    "mark_job_run",
    "run_job",
]