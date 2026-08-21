import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.graphs.orchestrator import create_social_pilot_graph
from app.schemas.state import SocialState, BrandProfile

def test_full_campaign_flow():
    print("\n--- Testing SocialPilot Full Campaign Flow (Mock Mode) ---\n")
    # 1. Setup Graph
    graph = create_social_pilot_graph()
    assert graph is not None
    
    # 2. Define Brand
    brand = BrandProfile(
        brand_name="Nexus AI",
        brand_voice="bold",
        target_audience="CTOs and Tech Leaders",
        content_pillars=["Generative AI", "Agentic Workflows", "Future of Work"],
        active_platforms=["linkedin", "twitter"]
    )
    
    # 3. Initialize State
    initial_state = SocialState(
        client_id="nexus_001",
        brand_profile=brand,
        task_type="campaign",
        messages=[],
        next_step=None,
        trend_data=None,
        generated_content=None,
        scheduling_status=None,
        analytics_report=None,
        requires_human_approval=False,
        escalation_reason=None
    )
    
    # 4. Invoke Graph
    print(f"Starting Campaign Automation for {brand.brand_name}...")
    final_state = graph.invoke(initial_state)
    
    # 5. Verify Results
    print("\n--- Execution Results ---")
    print(f"Task Type: {final_state.get('task_type')}")
    print(f"Trend Data: {final_state.get('trend_data')}")
    print(f"Content: {final_state.get('generated_content')}")
    print(f"Scheduling: {final_state.get('scheduling_status')}")
    print(f"Messages Log: {final_state.get('messages')}")
    
    assert final_state.get("trend_data") is not None, "trend_data was not populated"
    assert final_state.get("generated_content") is not None, "generated_content was not populated"
    assert final_state.get("scheduling_status") is not None, "scheduling_status was not populated"
    print("\n[SUCCESS] Full Campaign Flow Experienced!")

if __name__ == "__main__":
    # Ensure Mock Mode is on for this test
    os.environ["MOCK_MODE"] = "true"
    test_full_campaign_flow()
