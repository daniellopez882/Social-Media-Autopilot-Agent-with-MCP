import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.graphs.orchestrator import create_social_pilot_graph
from app.schemas.state import SocialState, BrandProfile

def test_graph_compilation():
    print("Testing SocialPilot Graph Compilation...")
    graph = create_social_pilot_graph()
    assert graph is not None, "Graph compilation returned None"
    print("[SUCCESS] Graph compiled successfully!")
    
    # Test state initialization
    brand = BrandProfile(
        brand_name="Test Brand",
        target_audience="Developers",
        content_pillars=["AI", "Python"],
        active_platforms=["twitter", "linkedin"]
    )
    state = SocialState(
        client_id="client_001",
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
    assert state["task_type"] == "campaign"
    assert state["client_id"] == "client_001"
    assert state["brand_profile"].brand_name == "Test Brand"
    print(f"[SUCCESS] State initialized for task: {state['task_type']}")

if __name__ == "__main__":
    test_graph_compilation()
