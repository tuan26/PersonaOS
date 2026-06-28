"""
Persona DNA Model — KOL Studio Phase 1: Personal Brand Memory Engine.

Stores the "DNA" extracted from a KOL's past content corpus:
personality mix, signature vocabulary, post structure, measurable style
metrics and a prose voice summary. This is the moat — the fingerprint the
generation layer uses to write *as the KOL*.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PersonaDNA(Base):
    """Extracted brand-voice fingerprint for a persona (one row per persona)."""

    __tablename__ = "persona_dna"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("personas.id", ondelete="CASCADE"),
        index=True,
        unique=True,
    )

    source_count: Mapped[int] = mapped_column(Integer, default=0)
    # how many past posts were analyzed

    # ── AI-extracted ─────────────────────────────────────────────
    personality_mix: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    # [{"trait": "hài hước", "percent": 70}, ...]
    signature_phrases: Mapped[list[str]] = mapped_column(JSON, default=list)
    post_structure: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # {"pattern": "Hook → Story → CTA", "notes": "..."}
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    tone: Mapped[str] = mapped_column(String(200), default="")
    voice_summary: Mapped[str] = mapped_column(Text, default="")
    dos: Mapped[list[str]] = mapped_column(JSON, default=list)
    donts: Mapped[list[str]] = mapped_column(JSON, default=list)

    # ── Deterministic style metrics (computed in Python) ─────────
    style_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # {"avg_post_chars": ..., "avg_words_per_sentence": ..., "emoji_per_post": ...}
    sample_excerpts: Mapped[list[str]] = mapped_column(JSON, default=list)

    # ── Voice fingerprint (centroid embedding of the corpus) ─────
    voice_vector: Mapped[list[float]] = mapped_column(JSON, default=list)
    # average embedding of sampled posts — used to score "giống X%"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
