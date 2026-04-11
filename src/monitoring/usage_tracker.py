from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.1},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 4.0})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


class UsageTracker:
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or (Path.home() / ".ai_news_agent")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.usage_file = self.storage_dir / "usage.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.usage_file.exists():
            with open(self.usage_file, "r") as f:
                return json.load(f)
        return {"days": {}, "last_updated": None}

    def _save(self):
        self._data["last_updated"] = datetime.now().isoformat()
        with open(self.usage_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def record_request(
        self,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        success: bool = True,
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._data["days"]:
            self._data["days"][today] = {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_requests": 0,
                "total_cost_usd": 0.0,
                "models": {},
            }

        day = self._data["days"][today]
        day["total_input_tokens"] += input_tokens
        day["total_output_tokens"] += output_tokens
        day["total_requests"] += 1

        cost = calculate_cost(model, input_tokens, output_tokens)
        day["total_cost_usd"] += cost

        if model not in day["models"]:
            day["models"][model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "requests": 0,
                "errors": 0,
                "cost_usd": 0.0,
            }

        day["models"][model]["input_tokens"] += input_tokens
        day["models"][model]["output_tokens"] += output_tokens
        day["models"][model]["requests"] += 1
        day["models"][model]["cost_usd"] += cost

        if not success:
            day["models"][model]["errors"] += 1

        self._save()
        self._check_budget_and_alert()

    def get_daily_summary(self, days: int = 7) -> dict:
        today = datetime.now()
        totals = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_requests": 0,
            "total_cost_usd": 0.0,
        }

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self._data["days"]:
                day = self._data["days"][date]
                totals["total_input_tokens"] += day["total_input_tokens"]
                totals["total_output_tokens"] += day["total_output_tokens"]
                totals["total_requests"] += day["total_requests"]
                totals["total_cost_usd"] += day["total_cost_usd"]

        return totals

    def _check_budget_and_alert(self):
        BUDGET_LIMIT_USD = 5.0
        
        current_month = datetime.now().strftime("%Y-%m")
        month_cost = sum(
            d_data["total_cost_usd"]
            for d_str, d_data in self._data.get("days", {}).items()
            if d_str.startswith(current_month)
        )
        
        if "alerts" not in self._data:
            self._data["alerts"] = {}
        
        alert_key_80 = f"{current_month}_80"
        alert_key_100 = f"{current_month}_100"
        
        from src.services.telegram_service import send_quota_alert
        
        if month_cost >= BUDGET_LIMIT_USD and not self._data["alerts"].get(alert_key_100):
            send_quota_alert("budget_100", f"${month_cost:.2f}")
            self._data["alerts"][alert_key_100] = True
            self._save()
        elif month_cost >= BUDGET_LIMIT_USD * 0.8 and not self._data["alerts"].get(alert_key_80):
            send_quota_alert("budget_80", f"${month_cost:.2f}/${BUDGET_LIMIT_USD}")
            self._data["alerts"][alert_key_80] = True
            self._save()

    def generate_report(self) -> str:
        summary = self.get_daily_summary(7)
        lines = [
            "📊 AI News Agent - Usage Report (7 ngày gần nhất)",
            "─" * 50,
            f"  Total Requests:      {summary['total_requests']:,}",
            f"  Input Tokens:        {summary['total_input_tokens']:,}",
            f"  Output Tokens:       {summary['total_output_tokens']:,}",
            f"  Total Cost:          ${summary['total_cost_usd']:.4f}",
            "─" * 50,
            f"  Avg Daily Cost:      ${summary['total_cost_usd'] / 7:.4f}",
            f"  Est. Monthly Cost:    ${summary['total_cost_usd'] * 30 / 7:.2f}",
        ]
        return "\n".join(lines)


_tracker: Optional[UsageTracker] = None


def get_tracker() -> UsageTracker:
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


def get_report() -> str:
    tracker = get_tracker()
    return tracker.generate_report()


def record_pipeline_run(
    model: str,
    provider: str,
    repo_count: int,
    paper_count: int,
    success: bool = True,
):
    """Ghi nhận một lần chạy pipeline vào usage tracker."""
    tracker = get_tracker()
    input_tokens = repo_count * 1000 + paper_count * 500
    output_tokens = repo_count * 1500 + paper_count * 800
    tracker.record_request(
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        success=success,
    )


__all__ = [
    "MODEL_PRICING",
    "UsageTracker",
    "calculate_cost",
    "get_tracker",
    "get_report",
    "record_pipeline_run",
]