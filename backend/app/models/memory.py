"""
Memory Models — Phase 2: Memory + Life Engine

Stores everything a persona has experienced: conversations, events, posts.
Provides the foundation for a persona to have a "life history".
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Memory(Base):
    """
    A memory entry — anything the persona has said, done, or experienced.

    Three categories:
    - long_term: Core identity (sinh năm 2000, thích mèo, quê ở...)
    - episodic: Events that happened (nhận nuôi mèo, đi Đà Lạt)
    - social: Remembering followers (User A là fan cũ, User B hay troll)
    """

    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    # ── Memory Category (NEW) ────────────────────────────────────
    memory_category: Mapped[str] = mapped_column(
        String(20), default="episodic", index=True
    )
    # "long_term" | "episodic" | "social"

    # ── Content ──────────────────────────────────────────────────
    memory_type: Mapped[str] = mapped_column(
        String(30), default="conversation", index=True
    )
    # conversation | event | post | learning | emotion | milestone

    title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Social Memory fields (NEW) ───────────────────────────────
    # When memory_category = "social", these track follower info
    follower_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    follower_platform: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    follower_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # e.g., "Fan cũ 3 tháng, hay khen dễ thương"

    # ── Metadata ─────────────────────────────────────────────────
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict
    )
    # Flexible extra data (e.g., sentiment, context, related entities)

    # ── Importance & Embedding ───────────────────────────────────
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    # How important is this memory? 0.0–1.0. Used for retrieval priority.

    embedding_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    # Reference to vector DB embedding (ChromaDB/Pinecone)

    # ── Timeline ─────────────────────────────────────────────────
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    persona: Mapped["Persona"] = relationship("Persona", back_populates="memories")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Memory(type={self.memory_type}, importance={self.importance})>"


class LifeEvent(Base):
    """
    A significant life event in the persona's timeline.
    These form the narrative arc of the persona's "life".

    Example: "Nhận nuôi mèo", "Mèo bị ốm", "Đưa mèo đi khám"
    """

    __tablename__ = "life_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    # ── Event Details ────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(
        String(30), default="life", index=True
    )
    # life | achievement | travel | health | relationship | work | hobby

    # ── Emotional Impact ─────────────────────────────────────────
    mood_before: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mood_after: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # e.g., "hào hứng", "lo lắng", "vui vẻ"

    # ── Timeline ─────────────────────────────────────────────────
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    # When did this happen in the persona's life?
    # Can be set in the future for planned events.

    is_completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    persona: Mapped["Persona"] = relationship("Persona", back_populates="life_events")  # noqa: F821

    def __repr__(self) -> str:
        return f"<LifeEvent(title={self.title}, date={self.event_date})>"
