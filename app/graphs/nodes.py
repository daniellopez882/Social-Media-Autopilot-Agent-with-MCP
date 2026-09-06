"""
Graph nodes.

Changes from the previous version, in order of how much they mattered:

* Mock mode is read when a node runs, not when the module is imported, and
  its default is off (app/config.py). Every mock result is prefixed
  ``[MOCK]`` so it cannot be mistaken for work that happened.
* The content node no longer appends the brand's first banned topic to the
  generated text "for testing purposes". That line made every brand with a
  banned list fail guardrails on every run, and it was the reason the
  repository's approval test passed.
* Guardrails use whole-word matching (app/guardrails.py). The hardcoded
  ``"politics" / "competitor"`` check labelled "(simulation)" is gone.
* Non-mock nodes return text. ``crew.kickoff()`` returns a ``CrewOutput``;
  storing that in an ``Optional[str]`` field and then returning the state
  from FastAPI failed JSON serialisation with a 500.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.factory import AgentFactory, crewai_module
from app.config import settings
from app.guardrails import evaluate
from app.schemas.state import BrandProfile, SocialState

logger = logging.getLogger("socialpilot.nodes")

MOCK_PREFIX = "[MOCK] "


def mock_mode() -> bool:
    """Read at call time. Tests and operators can change it without re-importing."""
    return settings.MOCK_MODE


def _brand(state: SocialState) -> dict[str, Any]:
    brand = state.get("brand_profile")
    if isinstance(brand, BrandProfile):
        return brand.model_dump()
    if isinstance(brand, dict):
        return brand
    return {}


def _text(result: Any) -> str:
    """Plain text from whatever crewai returned."""
    raw = getattr(result, "raw", None)
    if isinstance(raw, str):
        return raw
    return str(result)


def _run_crew(agent: Any, description: str, expected_output: str) -> str:
    crewai = crewai_module()
    task = crewai.Task(description=description, expected_output=expected_output, agent=agent)
    crew = crewai.Crew(agents=[agent], tasks=[task], verbose=settings.LOG_LEVEL == "DEBUG")
    return _text(crew.kickoff())


# -- nodes ------------------------------------------------------------------


def trend_analyzer_node(state: SocialState) -> dict[str, Any]:
    brand = _brand(state)
    pillars = ", ".join(brand.get("content_pillars", [])) or "(no pillars set)"
    if mock_mode():
        return {"trend_data": f"{MOCK_PREFIX}trends for {pillars}: #MockTrendOne, #MockTrendTwo"}

    agent = AgentFactory(brand).create_trend_analyzer()
    text = _run_crew(
        agent,
        f"Identify current trends relevant to {brand.get('brand_name', 'the brand')} "
        f"in these areas: {pillars}.",
        "Top 3 trends with a content angle for each, as JSON.",
    )
    return {"trend_data": text}


def content_generator_node(state: SocialState) -> dict[str, Any]:
    brand = _brand(state)
    platforms = ", ".join(brand.get("active_platforms", [])) or "(no platforms set)"
    if mock_mode():
        return {
            "generated_content": (
                f"{MOCK_PREFIX}1. A post about {brand.get('brand_name', 'the brand')} "
                f"for {platforms}. 2. A second post."
            )
        }

    agent = AgentFactory(brand).create_content_generator()
    text = _run_crew(
        agent,
        f"Write posts based on this trend data: {state.get('trend_data') or '(none)'}. "
        f"Target platforms: {platforms}.",
        "A list of posts, each with a hook, caption and visual brief.",
    )
    return {"generated_content": text[: settings.MAX_CONTENT_CHARS]}


def guardrails_node(state: SocialState) -> dict[str, Any]:
    """
    Hold content for a human when it names a banned topic.

    Whole-word matching. The previous substring check held a post containing
    "start" for a brand that banned "art".
    """
    content = state.get("generated_content") or ""
    result = evaluate(content, _brand(state).get("banned_topics", []))
    if result.requires_human_approval:
        logger.info("guardrails held content for %s: %s", state.get("client_id"), result.reason)
        return {"requires_human_approval": True, "escalation_reason": result.reason}
    return {"requires_human_approval": False, "escalation_reason": None}


def campaign_scheduler_node(state: SocialState) -> dict[str, Any]:
    brand = _brand(state)
    if mock_mode():
        return {"scheduling_status": f"{MOCK_PREFIX}nothing was scheduled; mock mode is on"}

    agent = AgentFactory(brand).create_campaign_scheduler()
    text = _run_crew(
        agent,
        f"Plan publishing times for this content: {state.get('generated_content') or '(none)'} "
        f"on {', '.join(brand.get('active_platforms', [])) or 'the configured platforms'}. "
        "Report which scheduling tool calls succeeded and which returned not_implemented.",
        "A scheduling report that states plainly what was and was not scheduled.",
    )
    return {"scheduling_status": text}


def engagement_responder_node(state: SocialState) -> dict[str, Any]:
    brand = _brand(state)
    messages = list(state.get("messages", []))
    if mock_mode():
        return {"messages": [*messages, f"{MOCK_PREFIX}no replies were sent; mock mode is on"]}

    agent = AgentFactory(brand).create_engagement_responder()
    text = _run_crew(
        agent,
        "Classify incoming engagement and draft replies. Flag anything needing a human.",
        "A report of drafted replies and escalations.",
    )
    return {"messages": [*messages, text]}


def analytics_reporter_node(state: SocialState) -> dict[str, Any]:
    brand = _brand(state)
    if mock_mode():
        return {"analytics_report": f"{MOCK_PREFIX}no metrics were fetched; mock mode is on"}

    agent = AgentFactory(brand).create_analytics_reporter()
    text = _run_crew(
        agent,
        "Produce a performance report from whatever metrics the tools return. "
        "Where a tool reports not_implemented, say that no data was available.",
        "A report with an executive summary and a per-platform breakdown.",
    )
    return {"analytics_report": text}
