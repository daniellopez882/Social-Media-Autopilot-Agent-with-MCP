from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.schemas.state import BrandProfile, SocialState
from app.graphs.orchestrator import create_social_pilot_graph

app = FastAPI(title="MCP Social Media Autopilot API")

# In-memory stores
BRAND_DB = {}
PENDING_APPROVALS = {}

class CampaignRequest(BaseModel):
    client_id: str
    task_type: str = "campaign"

@app.get("/health")
async def health_check():
    return {"status": "online", "system": "SocialPilot"}

@app.post("/client/profile")
async def create_profile(profile: BrandProfile, client_id: str):
    BRAND_DB[client_id] = profile
    return {"message": "Profile created", "client_id": client_id}

@app.post("/run")
async def run_automation(request: CampaignRequest):
    if request.client_id not in BRAND_DB:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    brand = BRAND_DB[request.client_id]
    
    # Initialize state as a dictionary for LangGraph compatibility or a controlled BaseModel
    initial_values = {
        "client_id": request.client_id,
        "brand_profile": brand,
        "task_type": request.task_type,
        "messages": [],
        "requires_human_approval": False
    }
    
    # Run the graph
    try:
        graph = create_social_pilot_graph()
        result = graph.invoke(initial_values)
        
        # Check if human intervention is needed
        if result.get("requires_human_approval"):
            import uuid
            approval_id = str(uuid.uuid4())
            PENDING_APPROVALS[approval_id] = result
            return {
                "status": "awaiting_approval",
                "approval_id": approval_id,
                "reason": result.get("escalation_reason"),
                "content": result.get("generated_content")
            }
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve/{approval_id}")
async def approve_content(approval_id: str):
    if approval_id not in PENDING_APPROVALS:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    state = PENDING_APPROVALS.pop(approval_id)
    # Resume by calling the scheduler node directly or restarting graph with approved status
    state["requires_human_approval"] = False
    state["task_type"] = "scheduling" # Set task to scheduling to skip previous steps
    
    try:
        graph = create_social_pilot_graph()
        result = graph.invoke(state)
        return {"message": "Content approved and scheduled", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reject/{approval_id}")
async def reject_content(approval_id: str, feedback: str = "Rejected by human"):
    if approval_id not in PENDING_APPROVALS:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    PENDING_APPROVALS.pop(approval_id)
    return {"message": "Content rejected", "feedback": feedback}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
