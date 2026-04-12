from __future__ import annotations

from datetime import date, timedelta

from src.config import get_settings, prepare_runtime_environment
from src.models import CuratedNewsletter, FormattedNewsletter, ResearchCollection
from src.tools import GithubTrendingRepoTool, HuggingFaceDailyPapersTool


prepare_runtime_environment()

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, before_kickoff, crew, task


@CrewBase
class AINewsCrew:
    """AI news crew."""

    agents_config = "../config/agents.yaml"
    tasks_config = "../config/tasks.yaml"

    agents: list[BaseAgent]
    tasks: list[Task]

    def __init__(
        self,
        repo_limit: int | None = None,
        paper_limit: int | None = None,
        paper_date: str | None = None,
    ) -> None:
        self.settings = get_settings()
        if repo_limit is not None and repo_limit <= 0:
            raise ValueError("repo_limit phải lớn hơn 0.")
        if paper_limit is not None and paper_limit <= 0:
            raise ValueError("paper_limit phải lớn hơn 0.")

        self.repo_limit = (
            repo_limit if repo_limit is not None else self.settings.default_repo_limit
        )
        self.paper_limit = (
            paper_limit
            if paper_limit is not None
            else self.settings.default_paper_limit
        )
        self.paper_date = paper_date

    @before_kickoff
    def inject_defaults(self, inputs: dict) -> dict:
        payload = dict(inputs or {})
        reference_date = date.today() - timedelta(days=1)
        payload.setdefault("repo_limit", self.repo_limit)
        payload.setdefault("paper_limit", self.paper_limit)
        payload.setdefault("paper_date", self.paper_date or reference_date.isoformat())
        payload.setdefault("run_date", reference_date.isoformat())
        return payload

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm=self.settings.build_crewai_llm(temperature=0.0),
            tools=[GithubTrendingRepoTool(), HuggingFaceDailyPapersTool()],
            verbose=True,
            allow_delegation=False,
            max_iter=8,
        )

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            llm=self.settings.build_crewai_llm(temperature=0.15),
            verbose=True,
            allow_delegation=False,
            max_iter=6,
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm=self.settings.build_crewai_llm(temperature=0.2),
            verbose=True,
            allow_delegation=False,
            max_iter=4,
        )

    @task
    def gather_task(self) -> Task:
        return Task(
            config=self.tasks_config["gather_task"],
            agent=self.researcher(),
            output_pydantic=ResearchCollection,
        )

    @task
    def summarize_task(self) -> Task:
        return Task(
            config=self.tasks_config["summarize_task"],
            agent=self.analyst(),
            context=[self.gather_task()],
            output_pydantic=CuratedNewsletter,
        )

    @task
    def format_task(self) -> Task:
        return Task(
            config=self.tasks_config["format_task"],
            agent=self.editor(),
            context=[self.summarize_task()],
            output_pydantic=FormattedNewsletter,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            cache=True,
        )

    def get_curated_newsletter(self) -> CuratedNewsletter:
        """Chạy crew với 2 tasks (gather + summarize), lấy CuratedNewsletter."""
        from crewai import Crew, Process
        
        gather = self.gather_task()
        summarize = self.summarize_task()
        
        mini_crew = Crew(
            agents=[self.researcher(), self.analyst()],
            tasks=[gather, summarize],
            process=Process.sequential,
            verbose=True,
        )
        result = mini_crew.kickoff()
        
        if hasattr(result, 'pydantic') and isinstance(result.pydantic, CuratedNewsletter):
            return result.pydantic
        raise ValueError(f"Cannot get CuratedNewsletter: {result}")
