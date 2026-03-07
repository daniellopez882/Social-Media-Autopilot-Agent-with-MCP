import os
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field

load_dotenv()

from typing import List, Optional, TypedDict, Dict, Any

class BrandProfile(BaseModel):
    brand_name: str
    brand_voice: str = "conversational"
    target_audience: str
    content_pillars: List[str] = Field(default_factory=list)
    banned_topics: List[str] = Field(default_factory=list)
    active_platforms: List[str] = Field(default_factory=list)
    posting_frequency: int = 3
    primary_goal: str = "engagement"
    competitor_accounts: List[str] = Field(default_factory=list)

class SocialState(TypedDict):
    client_id: str
    brand_profile: BrandProfile
    task_type: str
    messages: List[str]
    next_step: Optional[str]
    trend_data: Optional[str]
    generated_content: Optional[str]
    scheduling_status: Optional[str]
    analytics_report: Optional[str]
    requires_human_approval: bool
    escalation_reason: Optional[str]
