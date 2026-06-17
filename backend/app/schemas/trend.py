"""
Trend Schemas — Phase 6: Trend Engine
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TrendResponse(BaseModel):
    """A detected trend."""
    source: str
    category: str
    title: str
    description: str
    hashtag: Optional[str] = None
    url: Optional[str] = None
    popularity_score: float
    engagement_count: int
    region: str


class TrendFetchRequest(BaseModel):
    """Request to fetch trends."""
    sources: list[str] = Field(
        default=["tiktok", "instagram", "reddit", "x"],
        description="Nguồn muốn lấy trend"
    )
    count_per_source: int = Field(default=15, ge=5, le=50)
    region: str = Field(default="global")


class TrendRecommendRequest(BaseModel):
    """Request trend-based content recommendations for a persona."""
    persona_id: str
    sources: list[str] = Field(default=["tiktok", "instagram", "reddit", "x"])
    count_per_source: int = Field(default=15, ge=5, le=50)
    top_k: int = Field(default=5, ge=1, le=10)
    use_ai: bool = Field(default=True)


class TrendRecommendationResponse(BaseModel):
    """A content recommendation based on a trend."""
    trend: TrendResponse
    relevance_score: float
    suggested_caption: str
    suggested_hashtags: list[str]
    content_type: str
    reasoning: str


class TrendRecommendListResponse(BaseModel):
    """List of trend recommendations for a persona."""
    persona_id: str
    persona_name: str
    total_trends_analyzed: int
    recommendations: list[TrendRecommendationResponse]
