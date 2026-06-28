"""
Trend-Fit Service — KOL Studio Phase 4.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.trend_fit_engine import TrendFitEngine
from app.services.persona_dna_service import PersonaDNAService
from app.services.persona_service import PersonaService
from app.services.trend_service import TrendService


class TrendFitService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(
        self,
        persona_id: str,
        sources: list[str] | None = None,
        top_k: int = 10,
    ) -> dict[str, Any]:
        persona = await PersonaService(self.db).get(persona_id)
        if not persona:
            raise ValueError("Không tìm thấy persona")
        dna = await PersonaDNAService(self.db).get(persona_id)

        trend_service = TrendService(self.db)
        try:
            trends = await trend_service.fetch_trends(
                sources=sources, count_per_source=8
            )
        finally:
            await trend_service.close()

        # already sorted by popularity; cap candidates for the LLM judge
        candidates = trends[: max(1, min(top_k, 15))]
        judged = await TrendFitEngine.judge_trends(persona, candidates, dna)

        return {
            "persona_id": persona_id,
            "persona_name": persona.name,
            "has_dna": dna is not None,
            "total_trends": len(trends),
            "results": judged,
        }
