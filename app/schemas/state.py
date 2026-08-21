import os
from typing import List, Optional, TypedDict, Dict, Any, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

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

class SocialState(TypedDict, total=False):
    client_id: str
    brand_profile: Union[BrandProfile, Dict[str, Any]]
    task_type: str
    messages: List[str]
    next_step: Optional[str]
    trend_data: Optional[str]
    generated_content: Optional[str]
    scheduling_status: Optional[str]
    analytics_report: Optional[str]
    requires_human_approval: bool
    escalation_reason: Optional[str]
