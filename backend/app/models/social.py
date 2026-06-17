"""
Social Media Models — Phase 4: Publishing Engine

Tracks connected social accounts and published posts across platforms.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SocialAccount(Base):
    """A social media account connected to a persona."""

    __tablename__ = "social_accounts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    platform: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # tiktok | instagram | facebook | threads | x

    username: Mapped[str] = mapped_column(String(100), nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Stats ────────────────────────────────────────────────────
    followers: Mapped[int] = mapped_column(Integer, default=0)
    following: Mapped[int] = mapped_column(Integer, default=0)
    posts_count: Mapped[int] = mapped_column(Integer, default=0)

    is_connected: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    persona: Mapped["Persona"] = relationship("Persona", back_populates="social_accounts")  # noqa: F821

    def __repr__(self) -> str:
        return f"<SocialAccount(platform={self.platform}, username={self.username})>"


class SocialPost(Base):
    """A post that has been published to a social platform."""

    __tablename__ = "social_posts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    content_post_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_posts.id", ondelete="CASCADE"), index=True
    )
    social_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("social_accounts.id", ondelete="CASCADE"), index=True
    )

    platform_post_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    platform_post_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Platform-specific stats ──────────────────────────────────
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
