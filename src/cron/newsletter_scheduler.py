from __future__ import annotations

import json
import re
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

HERMES_DIR = Path.home() / ".ai_news_agent"
CRON_DIR = HERMES_DIR / "cron"
JOBS_FILE = CRON_DIR / "jobs.json"
OUTPUT_DIR = CRON_DIR / "output"


def ensure_dirs(cron_dir: Path | None = None):
    target_dir = cron_dir or CRON_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR if target_dir == CRON_DIR else target_dir / "output"
    output.mkdir(parents=True, exist_ok=True)


def _parse_duration(s: str) -> int:
    match = re.match(r"^(\d+)\s*(m|min|h|hr|d|day)$", s.lower())
    if not match:
        raise ValueError(f"Invalid duration: '{s}'")
    value = int(match.group(1))
    unit = match.group(2)[0]
    multipliers = {"m": 1, "h": 60, "d": 1440}
    return value * multipliers[unit]


def parse_schedule(schedule: str) -> dict:
    schedule = schedule.strip().lower()
    parts = schedule.split()

    if len(parts) >= 5 and all(re.match(r"^[\d\*\-,/]+$", p) for p in parts[:5]):
        return {"kind": "cron", "expr": schedule, "display": schedule}

    if schedule.startswith("every "):
        duration_str = schedule[6:].strip()
        minutes = _parse_duration(duration_str)
        return {"kind": "interval", "minutes": minutes, "display": f"every {minutes}m"}

    try:
        minutes = _parse_duration(schedule)
        run_at = datetime.now() + timedelta(minutes=minutes)
        return {"kind": "once", "minutes": minutes, "run_at": run_at.isoformat(), "display": f"once in {schedule}"}
    except ValueError:
        pass

    raise ValueError(
        f"Invalid schedule '{schedule}'. Use:\n"
        f"  - '30m' (one-shot)\n"
        f"  - 'every 30m' (recurring)\n"
        f"  - '0 9 * * *' (cron: daily at 9am)\n"
    )


def _compute_next_run(schedule: dict) -> Optional[str]:
    now = datetime.now()
    if schedule["kind"] == "once":
        return schedule.get("run_at")
    if schedule["kind"] == "interval":
        return (now + timedelta(minutes=schedule["minutes"])).isoformat()
    if schedule["kind"] == "cron":
        return _compute_cron_next(schedule["expr"])
    return None


def _compute_cron_next(expr: str) -> str:
    try:
        from croniter import croniter
        cron = croniter(expr, datetime.now())
        return cron.get_next(datetime).isoformat()
    except Exception:
        return (datetime.now() + timedelta(days=1)).isoformat()


class NewsletterJob(BaseModel):
    id: str
    name: str
    prompt: str
    repo_limit: int = 5
    paper_limit: int = 8
    schedule: dict
    schedule_display: str
    repeat: Optional[dict] = None
    enabled: bool = True
    state: str = "scheduled"
    deliver: str = "telegram"
    created_at: str
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None


def create_newsletter_job(
    schedule: str,
    repo_limit: int = 5,
    paper_limit: int = 8,
    deliver: str = "telegram",
    repeat: Optional[int] = None,
    cron_dir: Path | None = None,
) -> dict:
    ensure_dirs(cron_dir)
    parsed = parse_schedule(schedule)
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()

    if parsed["kind"] == "once" and repeat is None:
        repeat = 1

    job = {
        "id": job_id,
        "name": "AI News Daily",
        "prompt": (
            f"Thu thập {repo_limit} repo GitHub trending và "
            f"{paper_limit} paper từ Hugging Face. "
            f"Tạo bản tin AI tiếng Việt và gửi qua {deliver}."
        ),
        "repo_limit": repo_limit,
        "paper_limit": paper_limit,
        "schedule": parsed,
        "schedule_display": parsed.get("display", schedule),
        "repeat": {"times": repeat, "completed": 0},
        "enabled": True,
        "state": "scheduled",
        "deliver": deliver,
        "created_at": now,
        "next_run_at": _compute_next_run(parsed),
        "last_run_at": None,
        "last_status": None,
        "last_error": None,
    }

    jobs = load_jobs(cron_dir)
    jobs.append(job)
    save_jobs(jobs, cron_dir)
    return job


def load_jobs(cron_dir: Path | None = None) -> list:
    target_dir = cron_dir or CRON_DIR
    jobs_file = target_dir / "jobs.json"
    if not jobs_file.exists():
        return []
    with open(jobs_file, "r", encoding="utf-8") as f:
        return json.load(f).get("jobs", [])


def save_jobs(jobs: list, cron_dir: Path | None = None):
    target_dir = cron_dir or CRON_DIR
    jobs_file = target_dir / "jobs.json"
    with open(jobs_file, "w", encoding="utf-8") as f:
        json.dump({"jobs": jobs, "updated_at": datetime.now().isoformat()}, f, indent=2)


def list_jobs(cron_dir: Path | None = None) -> list:
    return load_jobs(cron_dir)


def remove_job(job_id: str, cron_dir: Path | None = None) -> bool:
    jobs = load_jobs(cron_dir)
    original_len = len(jobs)
    jobs = [j for j in jobs if j["id"] != job_id]
    if len(jobs) < original_len:
        save_jobs(jobs, cron_dir)
        return True
    return False


def trigger_job(job_id: str, cron_dir: Path | None = None):
    jobs = load_jobs(cron_dir)
    for job in jobs:
        if job["id"] == job_id:
            job["next_run_at"] = datetime.now().isoformat()
            job["enabled"] = True
            job["state"] = "scheduled"
            save_jobs(jobs, cron_dir)
            return job
    return None


def get_due_jobs(cron_dir: Path | None = None) -> list:
    jobs = load_jobs(cron_dir)
    now = datetime.now()
    due = []
    for job in jobs:
        if not job.get("enabled", True):
            continue
        next_run = job.get("next_run_at")
        if not next_run:
            continue
        try:
            next_run_dt = datetime.fromisoformat(next_run)
        except ValueError:
            continue
        if next_run_dt <= now:
            due.append(job)
    return due


def mark_job_run(
    job_id: str,
    success: bool,
    error: str | None = None,
    cron_dir: Path | None = None,
):
    jobs = load_jobs(cron_dir)
    for job in jobs:
        if job["id"] == job_id:
            job["last_run_at"] = datetime.now().isoformat()
            job["last_status"] = "success" if success else "failed"
            job["last_error"] = error
            schedule = job.get("schedule", {})
            if schedule.get("kind") in ("cron", "interval"):
                job["next_run_at"] = _compute_next_run(schedule)
            job["state"] = "completed"
            save_jobs(jobs, cron_dir)
            return job
    return None