"""
Revenue Plan Service — KOL Studio Phase 5.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.revenue_engine import RevenueEngine, compute_math
from app.services.content_service import ContentService
from app.services.monetization_service import MonetizationService
from app.services.persona_dna_service import PersonaDNAService
from app.services.persona_service import PersonaService


class RevenuePlanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(
        self,
        persona_id: str,
        goal_type: str = "percent",
        goal_value: float = 20.0,
        days: int = 30,
    ) -> dict[str, Any]:
        persona = await PersonaService(self.db).get(persona_id)
        if not persona:
            raise ValueError("Không tìm thấy persona")

        money = MonetizationService(self.db)
        current = await money.revenue_summary(persona_id)
        products = await money.list_products(persona_id)
        prod_dicts = [
            {
                "name": p.name,
                "category": p.category,
                "commission_rate": p.commission_rate,
                "total_clicks": p.total_clicks,
                "total_conversions": p.total_conversions,
                "total_revenue": p.total_revenue,
            }
            for p in products
        ]

        R = float(current.get("total_revenue", 0) or 0)
        if goal_type == "amount":
            target = float(goal_value)
        else:  # percent
            target = R * (1 + float(goal_value) / 100.0)
            if R == 0:
                # no baseline to grow from — treat goal_value as absolute target
                target = float(goal_value)

        math_block = compute_math(current, target)

        dna = await PersonaDNAService(self.db).get(persona_id)
        try:
            insights = await ContentService(self.db).get_insights(persona_id)
        except Exception:
            insights = {}

        plan = await RevenueEngine.plan(
            persona=persona,
            current=current,
            products=prod_dicts,
            math_block=math_block,
            days=days,
            dna=dna,
            insights=insights,
        )

        return {
            "persona_id": persona_id,
            "persona_name": persona.name,
            "has_dna": dna is not None,
            "has_products": len(prod_dicts) > 0,
            "current": current,
            "math": math_block,
            "strategy": plan.get("strategy", ""),
            "focus_products": plan.get("focus_products", []),
            "plan": plan.get("plan", []),
            "warnings": plan.get("warnings", []),
        }
