import sys
import os
import json
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app

client = TestClient(app)
client_id = "test_safety"

# Profile with a sensitive topic
profile = {
    "brand_name": "SafeBrand",
    "brand_voice": "formal",
    "target_audience": "General",
    "content_pillars": ["Safety"],
    "active_platforms": ["twitter"],
    "banned_topics": ["politics", "CompetitorX"]
}

def test_full_approval_loop():
    print("--- Testing Approval Workflow ---")
    
    # 1. Register
    reg_resp = client.post(f"/client/profile?client_id={client_id}", json=profile)
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    assert reg_resp.json().get("client_id") == client_id
    
    # 2. Run Automation
    # In mock setup, the guardrail node is sensitive to keywords and triggers approval.
    print("Running campaign (expecting guardrail trigger)...")
    r = client.post("/run", json={"client_id": client_id})
    assert r.status_code == 200, f"Run failed: {r.text}"
    data = r.json()
    
    assert data.get("status") == "awaiting_approval", f"Expected awaiting_approval, got {data}"
    approval_id = data.get("approval_id")
    assert approval_id is not None, "Missing approval_id"
    assert "Guardrail Alert" in data.get("reason", "")
    print(f"[SUCCESS] Guardrail Triggered! Approval ID: {approval_id}")
    print(f"Reason: {data['reason']}")
    
    # 3. Approve
    print("\nSending Human Approval...")
    r_app = client.post(f"/approve/{approval_id}")
    assert r_app.status_code == 200, f"Approval failed: {r_app.text}"
    app_data = r_app.json()
    assert app_data.get("message") == "Content approved and scheduled"
    assert "scheduling_status" in app_data.get("result", {})
    print(f"Response: {app_data['message']}")
    print(f"Final Status: {app_data['result']['scheduling_status']}")

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "system": "SocialPilot"}

if __name__ == "__main__":
    os.environ["MOCK_MODE"] = "true"
    test_health_check()
    test_full_approval_loop()
