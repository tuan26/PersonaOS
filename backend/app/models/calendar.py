"""
Content Calendar Model — KOL Studio Phase 3.

A 30-day content plan: one row per planned day. Each item has a content
"pillar" (knowledge / story / sales) so the plan follows a funnel ratio
(default 70/20/10) instead of random posting. An item can be turned into a
real voiced draft (linked via content_post_id) using the Voice engine.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CalendarItem(Base):
    """A single planned content slot for a persona."""

    __tablename__ = "calendar_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id", ondelete="CASCADE"), index=True
    )

    plan_date: Mapped[date] = mapped_column(Date, index=True)
    day_index: Mapped[int] = mapped_column(Integer, default=0)

    pillar: Mapped[str] = mapped_column(String(20), default="knowledge")
    # knowledge | story | sales
    topic: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    hook: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(20), default="planned", index=True)
    # planned | drafted | done
    content_post_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # link to the generated ContentPost draft

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
