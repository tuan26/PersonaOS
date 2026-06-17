"""
Story Model — The heart of PersonaOS.

A Story is a narrative arc that defines what happens in a persona's life
over a period (week, month, quarter). Stories generate:
- Life Events (on the timeline)
- Content Ideas (for Content Engine)
- Emotional arcs (for authentic character development)

Flow: Persona → Story Engine → Memory → Content → Publish → Community
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Story(Base):
    """A narrative arc in a persona's life."""

    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    # ── Story Identity ───────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Time Scope ───────────────────────────────────────────────
    # "1_week" | "1_month" | "3_months"
    time_scope: Mapped[str] = mapped_column(String(20), default="1_month")
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # ── Theme ────────────────────────────────────────────────────
    # "travel" | "work" | "romance" | "lifestyle" | "health" | "hobby"
    theme: Mapped[str] = mapped_column(String(30), default="lifestyle", index=True)

    # ── Emotional Arc ────────────────────────────────────────────
    # Sequence of moods: ["hào hứng", "lo lắng", "nhẹ nhõm", "hạnh phúc"]
    emotional_arc: Mapped[list[str]] = mapped_column(JSON, default=list)

    # ── Story Milestones (sub-events) ────────────────────────────
    # Structure: [
    #   {"week": 1, "title": "Nhận nuôi Miu", "mood": "hào hứng",
    #    "content_ideas": ["caption về ngày đầu đón mèo", "story khoe mèo"]},
    #   ...
    # ]
    milestones: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # ── Status ───────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Progress ─────────────────────────────────────────────────
    current_milestone: Mapped[int] = mapped_column(Integer, default=0)
    # Which milestone is "now" happening

    # ── Generated Content Count ──────────────────────────────────
    events_generated: Mapped[int] = mapped_column(Integer, default=0)
    posts_generated: Mapped[int] = mapped_column(Integer, default=0)

    # ── AI Generation Meta ───────────────────────────────────────
    generation_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Story(title={self.title}, theme={self.theme}, scope={self.time_scope})>"
