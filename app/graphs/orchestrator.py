"""
The graph.

``create_social_pilot_graph()`` was called -- and the graph recompiled -- on
every ``/run`` and every ``/approve``. ``get_graph()`` compiles once.

An unknown ``task_type`` used to route to ``END``, which made ``/run`` return
200 with nothing done. The request model rejects unknown values with a 422
first; this node raising is the second line, for callers that bypass the API.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, StateGraph

from app.graphs.nodes import (
    analytics_reporter_node,
    campaign_scheduler_node,
    content_generator_node,
    engagement_responder_node,
    guardrails_node,
    trend_analyzer_node,
)
from app.schemas.state import TASK_TYPES, SocialState

ENTRY_NODE: dict[str, str] = {
    "campaign": "trend_analyzer",
    "content": "content_generator",
    "engagement": "engagement_responder",
    "analytics": "analytics_reporter",
    "scheduling": "campaign_scheduler",
}
assert set(ENTRY_NODE) == set(TASK_TYPES)


def orchestrator_node(state: SocialState) -> dict[str, Any]:
    task_type = state.get("task_type")
    if task_type not in ENTRY_NODE:
        raise ValueError(f"unknown task_type {task_type!r}; expected one of {TASK_TYPES}")
    return {"next_step": ENTRY_NODE[task_type]}


def _after_guardrails(state: SocialState) -> str:
    return END if state.get("requires_human_approval") else "campaign_scheduler"


def build_graph():
    workflow = StateGraph(SocialState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("trend_analyzer", trend_analyzer_node)
    workflow.add_node("content_generator", content_generator_node)
    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("campaign_scheduler", campaign_scheduler_node)
    workflow.add_node("engagement_responder", engagement_responder_node)
    workflow.add_node("analytics_reporter", analytics_reporter_node)

    workflow.set_entry_point("orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        lambda state: state["next_step"],
        {name: name for name in ENTRY_NODE.values()},
    )

    workflow.add_edge("trend_analyzer", "content_generator")
    workflow.add_edge("content_generator", "guardrails")
    workflow.add_conditional_edges(
        "guardrails", _after_guardrails, {"campaign_scheduler": "campaign_scheduler", END: END}
    )
    workflow.add_edge("campaign_scheduler", END)
    workflow.add_edge("engagement_responder", END)
    workflow.add_edge("analytics_reporter", END)

    return workflow.compile()


@lru_cache(maxsize=1)
def get_graph():
    """The compiled graph, built once per process."""
    return build_graph()


# Kept for callers of the old name.
create_social_pilot_graph = build_graph
