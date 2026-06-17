"""
Community Models — Phase 5: Community Engine

Tracks comments, inbox messages, and auto-reply configurations
for automated community interaction.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Float, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Comment(Base):
    """A comment on a persona's post."""

    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    platform_comment_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    post_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Sentiment ────────────────────────────────────────────────
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # positive | neutral | negative
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Reply ────────────────────────────────────────────────────
    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InboxMessage(Base):
    """A direct message received by a persona."""

    __tablename__ = "inbox_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AutoReply(Base):
    """Auto-reply rule configuration."""

    __tablename__ = "auto_replies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    trigger_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    trigger_sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reply_template: Mapped[str] = mapped_column(Text, nullable=False)
    # Template with {name}, {content} placeholders

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
