import httpx
import json

base_url = "http://127.0.0.1:8000"
client_id = "nex_01"

profile = {
    "brand_name": "Nexus",
    "brand_voice": "bold",
    "target_audience": "Tech Leaders",
    "content_pillars": ["AI", "Automation"],
    "active_platforms": ["twitter", "linkedin"]
}

try:
    print(f"Registering profile for {client_id}...")
    r1 = httpx.post(f"{base_url}/client/profile?client_id={client_id}", json=profile)
    print(f"Status: {r1.status_code}, Response: {r1.text}")
    
    print(f"\nRunning automation for {client_id}...")
    r2 = httpx.post(f"{base_url}/run", json={"client_id": client_id})
    print(f"Status: {r2.status_code}")
    if r2.status_code == 200:
        print("Success! Final State:")
        print(json.dumps(r2.json(), indent=2))
    else:
        print(f"Error: {r2.text}")

except Exception as e:
    print(f"Request failed: {e}")
