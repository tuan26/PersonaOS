"""
Monetization Schemas — Phase 7.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    persona_id: str
    name: str
    category: str = "general"
    affiliate_url: str = ""  # optional — add the idea now, paste the link later
    platform: str = "custom"
    commission_rate: float = Field(default=0.0, ge=0, le=100)


class ProductResponse(BaseModel):
    id: str
    persona_id: str
    name: str
    category: str
    affiliate_url: str
    platform: str
    commission_rate: float
    total_clicks: int
    total_conversions: int
    total_revenue: float
    conversion_rate: float
    is_active: bool

    model_config = {"from_attributes": True}


class PromoRequest(BaseModel):
    persona_id: str
    product_id: str


class RevenueSummary(BaseModel):
    persona_id: str
    product_count: int
    total_clicks: int
    total_conversions: int
    total_revenue: float
    avg_conversion_rate: float
