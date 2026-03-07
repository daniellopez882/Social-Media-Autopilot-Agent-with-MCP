import httpx
import json
import time

base_url = "http://127.0.0.1:8000"
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
    httpx.post(f"{base_url}/client/profile?client_id={client_id}", json=profile)
    
    # 2. Run Automation
    # Note: In our current mock setup, the guardrail node is sensitive to keywords.
    # We'll trigger it!
    print("Running campaign (expecting guardrail trigger)...")
    r = httpx.post(f"{base_url}/run", json={"client_id": client_id})
    data = r.json()
    
    if data.get("status") == "awaiting_approval":
        approval_id = data["approval_id"]
        print(f"✅ Guardrail Triggered! Approval ID: {approval_id}")
        print(f"Reason: {data['reason']}")
        
        # 3. Approve
        print("\nSending Human Approval...")
        r_app = httpx.post(f"{base_url}/approve/{approval_id}")
        print(f"Response: {r_app.json()['message']}")
        print(f"Final Status: {r_app.json()['result']['scheduling_status']}")
    else:
        print("❌ Failed to trigger guardrail. Check node logic.")

if __name__ == "__main__":
    test_full_approval_loop()
