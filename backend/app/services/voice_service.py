"""
Voice Service — KOL Studio Phase 2: generate-in-voice + score.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.voice_engine import VoiceEngine
from app.services.persona_dna_service import PersonaDNAService
from app.services.persona_service import PersonaService


class VoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(
        self,
        persona_id: str,
        topic: str,
        content_type: str = "post",
    ) -> dict[str, Any]:
        """Generate a post in the KOL's voice and score how on-voice it is."""
        persona = await PersonaService(self.db).get(persona_id)
        if not persona:
            raise ValueError("Không tìm thấy persona")
        dna = await PersonaDNAService(self.db).get(persona_id)
        if not dna:
            raise LookupError("Persona chưa có DNA. Hãy phân tích bài cũ (Giai đoạn 1) trước.")

        gen = await VoiceEngine.generate_in_voice(persona, dna, topic, content_type)
        caption = gen.get("caption", "")
        score = await VoiceEngine.score_voice_match(caption, dna) if caption else {}
        return {
            "persona_id": persona_id,
            "persona_name": persona.name,
            "topic": topic,
            "caption": caption,
            "hashtags": gen.get("hashtags", []),
            "match": score,
        }

    async def score(self, persona_id: str, text: str) -> dict[str, Any]:
        """Score an arbitrary text against the KOL's voice."""
        dna = await PersonaDNAService(self.db).get(persona_id)
        if not dna:
            raise LookupError("Persona chưa có DNA. Hãy phân tích bài cũ trước.")
        return await VoiceEngine.score_voice_match(text, dna)
