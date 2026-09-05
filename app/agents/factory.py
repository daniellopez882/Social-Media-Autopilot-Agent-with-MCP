"""
Builds the crewai agents.

Two things the previous version did that hid failures until the worst moment:

* ``try: from crewai import Agent / except ImportError: class Agent: ...`` --
  a stand-in class that accepted any keyword and did nothing. With crewai
  absent, agents "constructed" fine and the failure moved to wherever the
  first real call happened.
* ``try: self.llm = ChatOpenAI(model="gpt-4o") / except Exception: self.llm =
  None`` -- a missing key was swallowed, ``llm=None`` was handed to every
  agent, and the error surfaced inside ``crew.kickoff()`` as whatever crewai
  makes of a null model.

Both now raise, with a message naming the setting, at the point of use. The
model name is configuration; the README used to describe a Claude/GPT-4 mix
that no code implemented.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.tools.social_tools import crewai_tools
from social_media_prompts import (
    ANALYTICS_REPORTER_PROMPT,
    CAMPAIGN_SCHEDULER_PROMPT,
    CONTENT_GENERATOR_PROMPT,
    ENGAGEMENT_RESPONDER_PROMPT,
    GUARDRAILS_PROMPT,
    TREND_ANALYZER_PROMPT,
    build_agent_prompt_with_brand,
)


class CrewAINotInstalled(RuntimeError):
    """crewai is required outside mock mode and is not importable."""


class LLMNotConfigured(RuntimeError):
    """A model is required outside mock mode and no credential is set."""


def crewai_module() -> Any:
    try:
        import crewai
    except ImportError as exc:
        raise CrewAINotInstalled(
            "crewai is not installed (it requires Python >=3.10,<3.14). "
            "Install it, or set MOCK_MODE=true to run without models."
        ) from exc
    return crewai


def build_llm() -> Any:
    """
    crewai's own LLM, with the key passed explicitly.

    Handing crewai a LangChain ``ChatOpenAI`` does not work the way it looks:
    crewai unwraps the object, reads the model name, and builds its own client
    -- taking the key from ``os.environ``. A key that lives only in ``.env``
    (read by pydantic-settings, never exported) is invisible to that path, and
    the failure is "Missing credentials" from inside ``crew.kickoff()`` with the
    key plainly configured.
    """
    api_key = settings.OPENAI_API_KEY.strip()
    if not api_key:
        raise LLMNotConfigured(
            "OPENAI_API_KEY is not set and MOCK_MODE is off. Set the key, or set MOCK_MODE=true."
        )
    return crewai_module().LLM(model=settings.OPENAI_MODEL, api_key=api_key, temperature=0.2)


class AgentFactory:
    def __init__(self, brand_profile: dict[str, Any], *, llm: Any = None) -> None:
        self.brand_profile = brand_profile
        self._llm = llm

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = build_llm()
        return self._llm

    def _agent(self, role: str, goal: str, prompt: str, *, with_tools: bool) -> Any:
        agent_cls = crewai_module().Agent
        return agent_cls(
            role=role,
            goal=goal,
            backstory=build_agent_prompt_with_brand(prompt, self.brand_profile),
            llm=self.llm,
            tools=crewai_tools() if with_tools else [],
            verbose=settings.LOG_LEVEL == "DEBUG",
            allow_delegation=False,
        )

    def create_trend_analyzer(self) -> Any:
        return self._agent(
            "Trend Analyzer",
            "Identify current, relevant trends for the brand",
            TREND_ANALYZER_PROMPT,
            with_tools=True,
        )

    def create_content_generator(self) -> Any:
        return self._agent(
            "Content Generator",
            "Write platform-appropriate posts for the brand",
            CONTENT_GENERATOR_PROMPT,
            with_tools=False,
        )

    def create_engagement_responder(self) -> Any:
        return self._agent(
            "Engagement Responder",
            "Draft replies in the brand's voice",
            ENGAGEMENT_RESPONDER_PROMPT,
            with_tools=True,
        )

    def create_analytics_reporter(self) -> Any:
        return self._agent(
            "Analytics Reporter",
            "Turn metrics into recommendations",
            ANALYTICS_REPORTER_PROMPT,
            with_tools=True,
        )

    def create_campaign_scheduler(self) -> Any:
        return self._agent(
            "Campaign Scheduler",
            "Plan publishing times for approved content",
            CAMPAIGN_SCHEDULER_PROMPT,
            with_tools=True,
        )

    def create_guardrails_agent(self) -> Any:
        return self._agent(
            "Brand Safety Officer",
            "Check content against the brand's constraints",
            GUARDRAILS_PROMPT,
            with_tools=False,
        )
