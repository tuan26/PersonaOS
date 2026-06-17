"""
Content Models — Phase 3: Content Engine

Stores generated content: captions, images, reels, video shorts.
Each post is tied to a persona's life events and memories.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ContentPost(Base):
    """
    A content post generated for a persona.
    Can be caption-only, image, reel, or video short.
    """

    __tablename__ = "content_posts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    # ── Content ──────────────────────────────────────────────────
    content_type: Mapped[str] = mapped_column(
        String(20), default="caption", index=True
    )
    # caption | image | reel | video | story | carousel

    title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSON, default=list)

    # ── Media ────────────────────────────────────────────────────
    media_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    # URLs to generated/stored images, videos

    # ── Context (why was this content created?) ──────────────────
    # Reference to a memory or life event that inspired this post
    inspired_by_memory_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )
    inspired_by_event_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )

    # ── AI Generation Meta ───────────────────────────────────────
    generation_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # What prompted this content? (trend, event, scheduled, etc.)

    # ── Status ───────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True
    )
    # draft | approved | scheduled | published | failed

    # ── Engagement (populated after publishing) ──────────────────
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Schedule ─────────────────────────────────────────────────
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    persona: Mapped["Persona"] = relationship("Persona", back_populates="content_posts")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ContentPost(type={self.content_type}, status={self.status})>"


class ContentSchedule(Base):
    """
    Content publishing schedule for a persona.
    Defines when and how often content is generated and posted.
    """

    __tablename__ = "content_schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    # ── Schedule Config ──────────────────────────────────────────
    posts_per_day: Mapped[int] = mapped_column(Integer, default=2)
    preferred_times: Mapped[list[str]] = mapped_column(
        JSON, default=["08:00", "12:00", "19:00"]
    )
    # Times in HH:MM format (timezone-aware)

    content_mix: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    # e.g., {"caption": 40, "image": 30, "reel": 20, "story": 10}

    # ── Active Days ──────────────────────────────────────────────
    active_days: Mapped[list[int]] = mapped_column(
        JSON, default=[0, 1, 2, 3, 4, 5, 6]
    )
    # 0=Monday, 6=Sunday

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
