"""
Trend Service — Phase 6: Trend detection and content recommendations.

Aggregates trends from all sources and generates persona-specific
content recommendations to maximize reach.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.trend_engine import Trend, TrendEngine, TrendRecommendation, TrendSource
from app.services.persona_service import PersonaService


class TrendService:
    """Manages trend detection and content recommendations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.persona_service = PersonaService(db)
        self.engine = TrendEngine()

    async def close(self):
        await self.engine.close()

    # ── Trend Fetching ───────────────────────────────────────────

    async def fetch_trends(
        self,
        sources: list[str] | None = None,
        count_per_source: int = 15,
        region: str = "global",
    ) -> list[dict[str, Any]]:
        """Fetch trends from specified sources."""
        trend_sources = None
        if sources:
            trend_sources = [TrendSource(s) for s in sources]

        trends = await self.engine.fetch_all_trends(
            sources=trend_sources,
            count_per_source=count_per_source,
            region=region,
        )

        return [self._trend_to_dict(t) for t in trends]

    # ── Persona Recommendations ──────────────────────────────────

    async def recommend_for_persona(
        self,
        persona_id: str,
        sources: list[str] | None = None,
        count_per_source: int = 15,
        top_k: int = 5,
        use_ai: bool = True,
    ) -> dict[str, Any]:
        """
        Fetch trends and generate persona-specific content recommendations.

        Returns top K content ideas with suggested captions and hashtags.
        """
        persona = await self.persona_service.get(persona_id)
        if not persona:
            raise ValueError(f"Persona not found: {persona_id}")

        # 1. Fetch trends
        trends = await self.engine.fetch_all_trends(
            sources=[TrendSource(s) for s in sources] if sources else None,
            count_per_source=count_per_source,
        )

        # 2. Generate recommendations
        recommendations = await self.engine.recommend_for_persona(
            persona=persona,
            trends=trends,
            top_k=top_k,
            use_ai=use_ai,
        )

        return {
            "persona_id": persona_id,
            "persona_name": persona.name,
            "total_trends_analyzed": len(trends),
            "recommendations": [
                {
                    "trend": self._trend_to_dict(r.trend),
                    "relevance_score": r.relevance_score,
                    "suggested_caption": r.suggested_caption,
                    "suggested_hashtags": r.suggested_hashtags,
                    "content_type": r.content_type,
                    "reasoning": r.reasoning,
                }
                for r in recommendations
            ],
        }

    # ── Bulk Recommendations (Multi-Persona) ─────────────────────

    async def recommend_all_active(
        self,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Generate trend recommendations for ALL active personas.
        Useful for dashboards and batch content planning.
        """
        personas = await self.persona_service.list_all(is_active=True, limit=100)

        # Fetch trends once
        trends = await self.engine.fetch_all_trends()

        results = []
        for persona in personas:
            recommendations = await self.engine.recommend_for_persona(
                persona=persona,
                trends=trends,
                top_k=top_k,
            )
            results.append({
                "persona_id": persona.id,
                "persona_name": persona.name,
                "total_trends": len(trends),
                "recommendations": [
                    {
                        "trend": self._trend_to_dict(r.trend),
                        "relevance_score": r.relevance_score,
                        "suggested_caption": r.suggested_caption,
                        "suggested_hashtags": r.suggested_hashtags,
                        "content_type": r.content_type,
                        "reasoning": r.reasoning,
                    }
                    for r in recommendations
                ],
            })

        return results

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _trend_to_dict(trend: Trend) -> dict[str, Any]:
        return {
            "source": trend.source.value,
            "category": trend.category.value,
            "title": trend.title,
            "description": trend.description,
            "hashtag": trend.hashtag,
            "url": trend.url,
            "popularity_score": trend.popularity_score,
            "engagement_count": trend.engagement_count,
            "region": trend.region,
        }
