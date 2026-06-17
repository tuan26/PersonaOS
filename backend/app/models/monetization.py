"""
Monetization Models — Phase 7-8: Monetization + Revenue Engine

Tracks affiliate products, click events, and conversions
for data-driven revenue optimization.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AffiliateProduct(Base):
    """A product/service being promoted via affiliate marketing."""

    __tablename__ = "affiliate_products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # travel | tech | beauty | fitness | food | fashion | etc.

    affiliate_url: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default="amazon")
    # amazon | shopee | lazada | tiktok_shop | custom

    commission_rate: Mapped[float] = mapped_column(Float, default=0.0)
    # Commission percentage

    # ── Performance ──────────────────────────────────────────────
    total_clicks: Mapped[int] = mapped_column(Integer, default=0)
    total_conversions: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_rate: Mapped[float] = mapped_column(Float, default=0.0)

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ClickEvent(Base):
    """A click on an affiliate link."""

    __tablename__ = "click_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("affiliate_products.id", ondelete="CASCADE"), index=True
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    source: Mapped[str] = mapped_column(String(50), default="post")
    # post | bio_link | story | comment

    user_identifier: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ConversionEvent(Base):
    """A successful conversion (purchase/signup) from an affiliate link."""

    __tablename__ = "conversion_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("affiliate_products.id", ondelete="CASCADE"), index=True
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    order_value: Mapped[float] = mapped_column(Float, default=0.0)
    commission_earned: Mapped[float] = mapped_column(Float, default=0.0)

    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    converted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
