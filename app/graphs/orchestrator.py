from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.schemas.state import SocialState
from app.graphs.nodes import (
    trend_analyzer_node,
    content_generator_node,
    campaign_scheduler_node,
    engagement_responder_node,
    analytics_reporter_node,
    guardrails_node
)

def orchestrator_node(state: SocialState) -> Dict[str, Any]:
    """
    Supervisor node that determines the starting point of the workflow.
    """
    task_type = state.get("task_type")
    
    if task_type == "campaign":
        return {"next_step": "trend_analyzer"}
    elif task_type == "content":
        return {"next_step": "content_generator"}
    elif task_type == "engagement":
        return {"next_step": "engagement_responder"}
    elif task_type == "analytics":
        return {"next_step": "analytics_reporter"}
    elif task_type == "scheduling":
        return {"next_step": "campaign_scheduler"}
    
    return {"next_step": END}

def create_social_pilot_graph():
    workflow = StateGraph(SocialState)
    
    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("trend_analyzer", trend_analyzer_node)
    workflow.add_node("content_generator", content_generator_node)
    workflow.add_node("campaign_scheduler", campaign_scheduler_node)
    workflow.add_node("engagement_responder", engagement_responder_node)
    workflow.add_node("analytics_reporter", analytics_reporter_node)
    workflow.add_node("guardrails", guardrails_node)
    
    # Set entry point
    workflow.set_entry_point("orchestrator")
    
    # Add conditional edges from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        lambda x: x.get("next_step"),
        {
            "trend_analyzer": "trend_analyzer",
            "content_generator": "content_generator",
            "engagement_responder": "engagement_responder",
            "analytics_reporter": "analytics_reporter",
            "campaign_scheduler": "campaign_scheduler",
            END: END
        }
    )
    
    # Add sequential edges for standard flows
    workflow.add_edge("trend_analyzer", "content_generator")
    workflow.add_edge("content_generator", "guardrails")
    workflow.add_edge("guardrails", "campaign_scheduler")
    workflow.add_edge("campaign_scheduler", END)
    
    workflow.add_edge("engagement_responder", END)
    workflow.add_edge("analytics_reporter", END)
    
    return workflow.compile()
