"""
Social Inbox Model — Unified inbox for all platforms.

Transforms "Chat" into a real social inbox that tracks:
- Instagram DM, Facebook Inbox, Threads, X messages
- Message status: new, pending, replied, ignored
- Prevents duplicate replies via message_id tracking
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SocialInboxMessage(Base):
    """A message received from any social platform, unified in one inbox."""

    __tablename__ = "social_inbox"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    # ── Platform Info ────────────────────────────────────────────
    platform: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # instagram | facebook | threads | x | tiktok
    platform_message_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    # Unique ID from platform — prevents duplicate replies

    # ── Sender ───────────────────────────────────────────────────
    sender_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sender_platform_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Message ──────────────────────────────────────────────────
    message_type: Mapped[str] = mapped_column(String(20), default="dm")
    # dm | comment_reply | mention | story_reply
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Status (NEW: lifecycle tracking) ─────────────────────────
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    # new → pending (AI đang xử lý) → replied | ignored
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── AI Analysis ──────────────────────────────────────────────
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # positive | neutral | negative
    sentiment_score: Mapped[float] = mapped_column(default=0.0)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    # 0=normal, 1=important, 2=urgent

    # ── AI Reply ─────────────────────────────────────────────────
    reply_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reply_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Metadata ─────────────────────────────────────────────────
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<SocialInbox(platform={self.platform}, status={self.status}, from={self.sender_name})>"
