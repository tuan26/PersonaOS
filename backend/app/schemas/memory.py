"""
Memory Schemas.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    """Create a memory entry."""
    memory_type: str = Field(default="conversation")
    title: Optional[str] = None
    content: str = Field(..., min_length=1)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    occurred_at: Optional[datetime] = None


class MemoryResponse(BaseModel):
    """Memory entry response."""
    id: str
    persona_id: str
    memory_type: str
    title: Optional[str] = None
    content: str
    importance: float
    metadata_: dict[str, Any]
    embedding_id: Optional[str] = None
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class LifeEventCreate(BaseModel):
    """Create a life event."""
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    event_type: str = Field(default="life")
    mood_before: Optional[str] = None
    mood_after: Optional[str] = None
    event_date: datetime
    is_completed: bool = False


class LifeEventResponse(BaseModel):
    """Life event response."""
    id: str
    persona_id: str
    title: str
    description: Optional[str] = None
    event_type: str
    mood_before: Optional[str] = None
    mood_after: Optional[str] = None
    event_date: datetime
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
