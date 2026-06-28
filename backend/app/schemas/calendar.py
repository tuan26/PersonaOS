"""
Content Calendar Schemas — KOL Studio Phase 3.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class CalendarGenerateRequest(BaseModel):
    persona_id: str
    days: int = Field(default=30, ge=7, le=60)
    start_date: Optional[date] = None  # default: today
    topics_hint: str = ""
    # funnel ratio (percent) — must roughly sum to 100
    knowledge_pct: int = Field(default=70, ge=0, le=100)
    story_pct: int = Field(default=20, ge=0, le=100)
    sales_pct: int = Field(default=10, ge=0, le=100)


class CalendarItemResponse(BaseModel):
    id: str
    persona_id: str
    plan_date: date
    day_index: int
    pillar: str
    topic: str
    title: str
    hook: str
    status: str
    content_post_id: Optional[str] = None

    model_config = {"from_attributes": True}
