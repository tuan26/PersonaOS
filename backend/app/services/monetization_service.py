"""
Monetization Service — Phase 7.

CRUD for affiliate products, click/conversion tracking, revenue summary,
plus AI wrappers (product suggestions + promo content).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.monetization_engine import MonetizationEngine
from app.models.monetization import AffiliateProduct, ClickEvent, ConversionEvent
from app.schemas.monetization import ProductCreate


class MonetizationService:
    """Manages affiliate products and revenue for a persona."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Products ─────────────────────────────────────────────────

    async def add_product(self, data: ProductCreate) -> AffiliateProduct:
        product = AffiliateProduct(
            persona_id=data.persona_id,
            name=data.name,
            category=data.category,
            affiliate_url=data.affiliate_url,
            platform=data.platform,
            commission_rate=data.commission_rate,
        )
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def list_products(self, persona_id: str) -> list[AffiliateProduct]:
        result = await self.db.execute(
            select(AffiliateProduct)
            .where(AffiliateProduct.persona_id == persona_id)
            .order_by(AffiliateProduct.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_product(self, product_id: str) -> AffiliateProduct | None:
        result = await self.db.execute(
            select(AffiliateProduct).where(AffiliateProduct.id == product_id)
        )
        return result.scalar_one_or_none()

    # ── Tracking ─────────────────────────────────────────────────

    async def record_click(
        self, product_id: str, persona_id: str, source: str = "post"
    ) -> AffiliateProduct | None:
        product = await self.get_product(product_id)
        if not product:
            return None
        self.db.add(ClickEvent(
            product_id=product_id, persona_id=persona_id, source=source
        ))
        product.total_clicks += 1
        if product.total_clicks:
            product.conversion_rate = round(
                product.total_conversions / product.total_clicks * 100, 2
            )
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def record_conversion(
        self,
        product_id: str,
        persona_id: str,
        order_value: float = 0.0,
    ) -> AffiliateProduct | None:
        product = await self.get_product(product_id)
        if not product:
            return None
        commission = round(order_value * product.commission_rate / 100, 2)
        self.db.add(ConversionEvent(
            product_id=product_id,
            persona_id=persona_id,
            order_value=order_value,
            commission_earned=commission,
        ))
        product.total_conversions += 1
        product.total_revenue += commission
        if product.total_clicks:
            product.conversion_rate = round(
                product.total_conversions / product.total_clicks * 100, 2
            )
        await self.db.flush()
        await self.db.refresh(product)
        return product

    # ── Revenue summary ──────────────────────────────────────────

    async def revenue_summary(self, persona_id: str) -> dict[str, Any]:
        result = await self.db.execute(
            select(
                func.count(AffiliateProduct.id),
                func.coalesce(func.sum(AffiliateProduct.total_clicks), 0),
                func.coalesce(func.sum(AffiliateProduct.total_conversions), 0),
                func.coalesce(func.sum(AffiliateProduct.total_revenue), 0.0),
                func.coalesce(func.avg(AffiliateProduct.conversion_rate), 0.0),
            ).where(AffiliateProduct.persona_id == persona_id)
        )
        cnt, clicks, conv, rev, avg_cr = result.one()
        return {
            "persona_id": persona_id,
            "product_count": int(cnt or 0),
            "total_clicks": int(clicks or 0),
            "total_conversions": int(conv or 0),
            "total_revenue": float(rev or 0.0),
            "avg_conversion_rate": round(float(avg_cr or 0.0), 2),
        }

    # ── AI ───────────────────────────────────────────────────────

    async def suggest_products(self, persona: Any, count: int = 5) -> dict[str, Any]:
        suggestions = await MonetizationEngine.suggest_products(persona, count)
        return {"persona_name": persona.name, "suggestions": suggestions}

    async def generate_promo(
        self, persona: Any, product: AffiliateProduct
    ) -> dict[str, Any]:
        from app.services.memory_service import MemoryService

        memories = await MemoryService(self.db).get_recent_memories(
            persona_id=persona.id, limit=3
        )
        return await MonetizationEngine.generate_promo(
            persona=persona,
            product_name=product.name,
            product_category=product.category,
            affiliate_url=product.affiliate_url,
            memories=memories,
        )
