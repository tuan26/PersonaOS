"""
Content Schemas.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContentGenerateRequest(BaseModel):
    """Request to generate content for a persona."""
    persona_id: str
    content_type: str = Field(default="caption")
    topic_hint: Optional[str] = None
    # Optional: reference specific memory/event
    inspired_by_memory_id: Optional[str] = None
    inspired_by_event_id: Optional[str] = None
    count: int = Field(default=1, ge=1, le=10)
    creativity: float = Field(default=0.8, ge=0.0, le=1.0)


class ContentDraftCreate(BaseModel):
    """Save an already-written caption (e.g. from a trend suggestion) as a draft."""
    persona_id: str
    caption: str
    hashtags: list[str] = Field(default_factory=list)
    content_type: str = Field(default="caption")
    source: Optional[str] = None  # e.g. "trend", to record where it came from


class ContentPostResponse(BaseModel):
    """Content post response."""
    id: str
    persona_id: str
    content_type: str
    title: Optional[str] = None
    caption: str
    hashtags: list[str]
    media_urls: list[str]
    status: str
    likes_count: int
    comments_count: int
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentScheduleCreate(BaseModel):
    """Create a content schedule."""
    persona_id: str
    posts_per_day: int = Field(default=2, ge=0, le=24)
    preferred_times: list[str] = Field(default=["08:00", "12:00", "19:00"])
    content_mix: dict[str, int] = Field(default_factory=dict)
    active_days: list[int] = Field(default=[0, 1, 2, 3, 4, 5, 6])
    is_active: bool = True


class ContentScheduleResponse(BaseModel):
    """Content schedule response."""
    id: str
    persona_id: str
    posts_per_day: int
    preferred_times: list[str]
    content_mix: dict[str, int]
    active_days: list[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
