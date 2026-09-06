"""
Shared types.

``load_dotenv()`` used to run here, at import of a *schema* module -- the one
place nobody would look for environment handling. Settings own that now
(app/config.py).

``task_type`` was an unconstrained ``str``. The orchestrator routed anything it
did not recognise to ``END``, so ``POST /run`` with ``task_type="nonsense"``
returned 200 and the untouched initial state: a silent no-op reported as
success. It is a ``Literal`` now, so an unknown value is a 422 before any graph
runs.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator

# "scheduling" is how an approved item re-enters the graph. It is not offered
# on the public request model: scheduling content that never passed through
# guardrails would bypass the one control the system has.
TaskType = Literal["campaign", "content", "engagement", "analytics", "scheduling"]
PublicTaskType = Literal["campaign", "content", "engagement", "analytics"]

TASK_TYPES: tuple[str, ...] = ("campaign", "content", "engagement", "analytics", "scheduling")
PUBLIC_TASK_TYPES: tuple[str, ...] = ("campaign", "content", "engagement", "analytics")

ShortText = Annotated[str, Field(min_length=1, max_length=200)]
ShortItem = Annotated[str, Field(min_length=1, max_length=100)]
ShortList = Annotated[list[ShortItem], Field(max_length=50)]


class BrandProfile(BaseModel):
    brand_name: ShortText
    brand_voice: ShortText = "conversational"
    target_audience: ShortText
    content_pillars: ShortList = Field(default_factory=list)
    banned_topics: ShortList = Field(default_factory=list)
    active_platforms: ShortList = Field(default_factory=list)
    posting_frequency: int = Field(default=3, ge=0, le=100)
    primary_goal: ShortText = "engagement"
    competitor_accounts: ShortList = Field(default_factory=list)

    @field_validator(
        "content_pillars", "banned_topics", "active_platforms", "competitor_accounts", mode="before"
    )
    @classmethod
    def _strip_and_drop_blanks(cls, value: object) -> object:
        # Before the per-item constraints run, so a blank entry is dropped
        # rather than rejected. Non-lists are left for pydantic to refuse.
        if not isinstance(value, list):
            return value
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class SocialState(TypedDict, total=False):
    client_id: str
    brand_profile: BrandProfile | dict[str, Any]
    task_type: str
    messages: list[str]
    next_step: str | None
    trend_data: str | None
    generated_content: str | None
    scheduling_status: str | None
    analytics_report: str | None
    requires_human_approval: bool
    escalation_reason: str | None
