import os
from typing import Dict, Any
from app.schemas.state import SocialState
from app.agents.factory import AgentFactory
from app.tools.social_tools import get_all_tools

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

try:
    from crewai import Task, Crew
except ImportError:
    MOCK_MODE = True

def trend_analyzer_node(state: SocialState) -> Dict[str, Any]:
    if MOCK_MODE:
        return {
            "trend_data": "MOCK TRENDS: #AI, #Automation, #SocialMedia",
            "next_step": "content_generator"
        }
    
    factory = AgentFactory(state["brand_profile"].model_dump())
    agent = factory.create_trend_analyzer()
    agent.tools = get_all_tools()
    
    task = Task(
        description=f"Analyze current trends for {state['brand_profile'].brand_name} in the industry focusing on {', '.join(state['brand_profile'].content_pillars)}.",
        expected_output="A structured JSON report of top 3 trends with content angles as per TREND_ANALYZER_PROMPT.",
        agent=agent
    )
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    
    return {"trend_data": result, "next_step": "content_generator"}

def content_generator_node(state: SocialState) -> Dict[str, Any]:
    if MOCK_MODE:
        content = "MOCK CONTENT: 1. Post about AI. 2. Post about Social Automation."
        # Inject trigger if brand has banned topics for testing flow
        brand = state.get("brand_profile")
        if brand and brand.banned_topics:
            content += f" (Note: We mention {brand.banned_topics[0]} for testing purposes)"
            
        return {
            "generated_content": content,
            "next_step": "guardrails"
        }
    
    factory = AgentFactory(state["brand_profile"].model_dump())
    
    task = Task(
        description=f"Generate social media content based on the following trend data: {state.get('trend_data')}. Target platforms: {', '.join(state['brand_profile'].active_platforms)}.",
        expected_output="A list of generated posts with hooks, captions, and visual briefs as per CONTENT_GENERATOR_PROMPT.",
        agent=agent
    )
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    
    return {"generated_content": result, "next_step": "campaign_scheduler"}

def campaign_scheduler_node(state: SocialState) -> Dict[str, Any]:
    if MOCK_MODE:
        return {
            "scheduling_status": "MOCK SCHEDULED: All posts queued for 9 AM.",
            "next_step": "__end__"
        }
    
    factory = AgentFactory(state["brand_profile"].model_dump())
    agent.tools = get_all_tools()
    
    task = Task(
        description=f"Schedule the following content: {state.get('generated_content')} for the client's active platforms.",
        expected_output="A scheduling confirmation report as per CAMPAIGN_SCHEDULER_PROMPT.",
        agent=agent
    )
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    
    return {"scheduling_status": result, "next_step": "__end__"}

def engagement_responder_node(state: SocialState) -> Dict[str, Any]:
    if MOCK_MODE:
        return {
            "messages": state.get("messages", []) + ["MOCK: Replied to 5 comments."],
            "next_step": "__end__"
        }
    factory = AgentFactory(state["brand_profile"].model_dump())
    agent = factory.create_engagement_responder()
    agent.tools = get_all_tools()
    
    # In a real scenario, this would be triggered by a specific message/comment
    task = Task(
        description="""
        Monitor and respond to incoming engagement.
        1. Classify the message into Categories A-E.
        2. Draft or send responses using the Reply Framework.
        3. Flag for human escalation if Category D or E.
        """,
        expected_output="A structured report of engagements handled, replies sent, and escalations flagged as per ENGAGEMENT_RESPONDER_PROMPT.",
        agent=agent
    )
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    
    return {"messages": state.get("messages", []) + [f"Engagement Cycle Complete: {result}"], "next_step": "__end__"}

def analytics_reporter_node(state: SocialState) -> Dict[str, Any]:
    if MOCK_MODE:
        return {
            "analytics_report": "MOCK REPORT: Reach up 20%, Engagement up 5%.",
            "next_step": "__end__"
        }
    factory = AgentFactory(state["brand_profile"].model_dump())
    agent = factory.create_analytics_reporter()
    agent.tools = get_all_tools()
    
    task = Task(
        description="""
        Generate a performance report for the last period.
        1. Fetch metrics for Instagram, X, and LinkedIn.
        2. Compare against industry benchmarks.
        3. Provide actionable recommendations (Do More, Stop, Test).
        4. Generate outputs in 3 formats: Slack summary, HTML report, and JSON data.
        """,
        expected_output="A full analytics payload including executive summary and platform breakdown as per ANALYTICS_REPORTER_PROMPT.",
        agent=agent
    )
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    
    return {"analytics_report": result, "next_step": "__end__"}

def guardrails_node(state: SocialState) -> Dict[str, Any]:
    """Ensures content follows brand safety and ethics guidelines."""
    # Simulation: Even in mock mode, we want to test the approval flow
    content = state.get("generated_content", "") or ""
    brand_profile = state.get("brand_profile")
    banned = brand_profile.banned_topics if brand_profile else []
    
    # Check for keywords
    triggered = []
    for topic in banned:
        if topic.lower() in content.lower():
            triggered.append(topic)
            
    # Also trigger if content looks sensitive (simulation)
    if "politics" in content.lower() or "competitor" in content.lower():
        triggered.append("Sensitive Topic")

    if triggered:
        return {
            "requires_human_approval": True,
            "escalation_reason": f"Guardrail Alert: Detected banned/sensitive topics: {', '.join(triggered)}"
        }
            
    return {"next_step": "campaign_scheduler"}
