"""
crew.py — Định nghĩa CrewAI agents, tasks và crew.

Pipeline gồm 3 bước:
  1. gather_task   → researcher agent dùng tools thu thập dữ liệu
  2. summarize_task → analyst agent chọn lọc và tóm tắt
  3. format_task   → formatter agent render HTML cho Telegram
"""

from __future__ import annotations

from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.settings import get_settings
from src.tools import (
    GithubTrendingRepoTool,
    GitHubRSSTool,
    AnthropicNewsTool,
    SecurityNewsTool,
    hacker_news_tool,
    arxiv_tool,
)

# Path đến file config — tương đối với file này (src/)
_CONFIG_DIR = Path(__file__).parent / "config"


@CrewBase
class AINewsCrew:
    """
    AI News Crew — thu thập, chọn lọc và format bản tin AI hàng ngày.

    Usage:
        crew = AINewsCrew(repo_limit=3)
        output = crew.crew().kickoff()
    """

    agents_config = str(_CONFIG_DIR / "agents.yaml")
    tasks_config = str(_CONFIG_DIR / "tasks.yaml")

    def __init__(self, repo_limit: int = 5):
        self.repo_limit = repo_limit
        self._llm = get_settings().build_llm()

    def _default_inputs(self) -> dict:
        return {"repo_limit": self.repo_limit}

    # ── Agents ────────────────────────────────────────────────────────────────

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm=self._llm,
            tools=[
                GithubTrendingRepoTool(),
                GitHubRSSTool(),
                AnthropicNewsTool(),
                SecurityNewsTool(),
                hacker_news_tool,
                arxiv_tool,
            ],
            verbose=False,
        )

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            llm=self._llm,
            verbose=False,
        )

    @agent
    def formatter(self) -> Agent:
        return Agent(
            config=self.agents_config["formatter"],
            llm=self._llm,
            verbose=False,
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @task
    def gather_task(self) -> Task:
        from src.models import ResearchCollection
        return Task(
            config=self.tasks_config["gather_task"],
            agent=self.researcher(),
            output_pydantic=ResearchCollection,
        )

    @task
    def summarize_task(self) -> Task:
        from src.models import CuratedNewsletter
        return Task(
            config=self.tasks_config["summarize_task"],
            agent=self.analyst(),
            context=[self.gather_task()],
            output_pydantic=CuratedNewsletter,
        )

    @task
    def format_task(self) -> Task:
        from src.models import FormattedNewsletter
        return Task(
            config=self.tasks_config["format_task"],
            agent=self.formatter(),
            context=[self.summarize_task()],
            output_pydantic=FormattedNewsletter,
        )

    # ── Crew ──────────────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            inputs=self._default_inputs(),
        )

    def get_curated_newsletter(self):
        """Chạy đến summarize_task và trả về CuratedNewsletter (không format HTML)."""
        from src.models import CuratedNewsletter
        partial_crew = Crew(
            agents=[self.researcher(), self.analyst()],
            tasks=[self.gather_task(), self.summarize_task()],
            process=Process.sequential,
            verbose=False,
            inputs=self._default_inputs(),
        )
        output = partial_crew.kickoff()
        if isinstance(output.pydantic, CuratedNewsletter):
            return output.pydantic
        for task_out in reversed(output.tasks_output or []):
            if isinstance(task_out.pydantic, CuratedNewsletter):
                return task_out.pydantic
        raise RuntimeError("Không lấy được CuratedNewsletter từ crew output")
