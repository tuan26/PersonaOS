"""
Community Schemas — Phase 5: Community Engine
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CommentAnalyzeRequest(BaseModel):
    """Request to analyze a comment."""
    persona_id: str
    comment_content: str = Field(..., min_length=1)
    commenter_name: str = Field(default="Người dùng")
    platform: str = Field(default="instagram")


class CommentAnalyzeResponse(BaseModel):
    """Result of comment analysis."""
    sentiment: str
    sentiment_score: float
    action: str
    suggested_reply: Optional[str] = None
    reason: str


class AutoReplyRequest(BaseModel):
    """Request to auto-reply to comments."""
    persona_id: str
    comments: list[dict[str, str]] = Field(
        ...,
        description='[{"id": "...", "content": "...", "commenter_name": "..."}]'
    )
    max_replies: int = Field(default=50, ge=1, le=200)
    current_mood: str = Field(default="bình thường")


class AutoReplyResultItem(BaseModel):
    """Single auto-reply result."""
    comment_id: str
    action: str  # reply | like | ignore
    reply_text: Optional[str] = None
    success: bool


class AutoReplyResponse(BaseModel):
    """Overall auto-reply results."""
    persona_id: str
    total_comments: int
    replied: int
    liked: int
    ignored: int
    results: list[AutoReplyResultItem]


class InboxReplyRequest(BaseModel):
    """Request to reply to an inbox message."""
    persona_id: str
    sender_name: str = Field(..., min_length=1)
    message_content: str = Field(..., min_length=1)
    platform: str = Field(default="instagram")


class InboxReplyResponse(BaseModel):
    """Inbox reply result."""
    persona_id: str
    persona_name: str
    sender_name: str
    reply_content: str


class InboxMessageCreate(BaseModel):
    """Add an incoming DM into the inbox (manual intake)."""
    persona_id: str
    sender_name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    platform: str = Field(default="instagram")


class InboxMessageResponse(BaseModel):
    """An inbox DM with derived status (new | pending | replied)."""
    id: str
    persona_id: str
    platform: str
    sender_name: str
    content: str
    replied: bool
    reply_content: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AutoReplyRuleCreate(BaseModel):
    """Create an auto-reply rule."""
    persona_id: str
    trigger_keywords: list[str] = Field(default_factory=list)
    trigger_sentiment: Optional[str] = None
    reply_template: str = Field(..., min_length=1)
    is_active: bool = True
    priority: int = 0


class AutoReplyRuleResponse(BaseModel):
    """Auto-reply rule."""
    id: str
    persona_id: str
    trigger_keywords: list[str]
    trigger_sentiment: Optional[str] = None
    reply_template: str
    is_active: bool
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True}
