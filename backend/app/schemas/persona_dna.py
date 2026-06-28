"""
Persona DNA Schemas — KOL Studio Phase 1.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DNAAnalyzeRequest(BaseModel):
    """Analyze a corpus of past posts to extract the persona's brand DNA."""
    persona_id: str
    posts: list[str] = Field(..., min_length=1, description="Các bài đăng cũ (text)")


class PersonaDNAResponse(BaseModel):
    id: str
    persona_id: str
    source_count: int
    personality_mix: list[dict[str, Any]]
    signature_phrases: list[str]
    post_structure: dict[str, Any]
    topics: list[str]
    tone: str
    voice_summary: str
    dos: list[str]
    donts: list[str]
    style_metrics: dict[str, Any]
    sample_excerpts: list[str]
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
