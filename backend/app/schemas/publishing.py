"""
Publishing Schemas — Phase 4: Publishing Engine
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SocialAccountCreate(BaseModel):
    """Connect a social media account to a persona."""
    persona_id: str
    platform: str = Field(..., description="tiktok | instagram | facebook | threads | x")
    username: str = Field(..., min_length=1, max_length=100)
    access_token: str
    platform_user_id: Optional[str] = None


class SocialAccountResponse(BaseModel):
    """Social account info."""
    id: str
    persona_id: str
    platform: str
    username: str
    platform_user_id: Optional[str] = None
    followers: int
    following: int
    posts_count: int
    is_connected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PublishRequest(BaseModel):
    """Request to publish content to social platforms."""
    persona_id: str
    content_post_id: Optional[str] = Field(
        default=None,
        description="ID của ContentPost (nếu đăng bài đã tạo sẵn)"
    )
    caption: Optional[str] = Field(
        default=None,
        description="Caption (nếu đăng trực tiếp, không qua ContentPost)"
    )
    media_urls: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(
        default=["instagram", "facebook", "threads", "x"],
        description="Nền tảng muốn đăng. Mặc định: tất cả"
    )
    schedule_time: Optional[datetime] = Field(
        default=None,
        description="Thời gian lên lịch đăng (None = đăng ngay)"
    )


class PublishResultResponse(BaseModel):
    """Result of a single platform publish."""
    platform: str
    success: bool
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    error_message: Optional[str] = None


class PublishAllResponse(BaseModel):
    """Response for publish-all operation."""
    persona_id: str
    results: list[PublishResultResponse]
    total_success: int
    total_failed: int


class ConnectionCheckRequest(BaseModel):
    """Check if platform credentials are valid."""
    platform: str
    access_token: str
    platform_user_id: Optional[str] = None


class ConnectionCheckResponse(BaseModel):
    """Connection check result."""
    platform: str
    is_connected: bool
    message: str
