"""
Persona DNA Service — KOL Studio Phase 1.

Runs the DNA extraction engine and upserts one PersonaDNA row per persona.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.persona_dna_engine import PersonaDNAEngine
from app.models.persona_dna import PersonaDNA


class PersonaDNAService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, persona_id: str) -> PersonaDNA | None:
        res = await self.db.execute(
            select(PersonaDNA).where(PersonaDNA.persona_id == persona_id)
        )
        return res.scalar_one_or_none()

    async def analyze_and_store(
        self,
        persona_id: str,
        posts: list[str],
        persona_name: str = "",
    ) -> PersonaDNA:
        """Extract DNA from the corpus and upsert it for the persona."""
        data: dict[str, Any] = await PersonaDNAEngine.analyze(posts, persona_name)

        dna = await self.get(persona_id)
        if dna is None:
            dna = PersonaDNA(persona_id=persona_id)
            self.db.add(dna)

        dna.source_count = data.get("source_count", 0)
        dna.personality_mix = data.get("personality_mix", [])
        dna.signature_phrases = data.get("signature_phrases", [])
        dna.post_structure = data.get("post_structure", {})
        dna.topics = data.get("topics", [])
        dna.tone = data.get("tone", "")
        dna.voice_summary = data.get("voice_summary", "")
        dna.dos = data.get("dos", [])
        dna.donts = data.get("donts", [])
        dna.style_metrics = data.get("style_metrics", {})
        dna.sample_excerpts = data.get("sample_excerpts", [])
        dna.voice_vector = data.get("voice_vector", [])

        await self.db.flush()
        await self.db.refresh(dna)
        return dna
