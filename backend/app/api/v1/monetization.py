"""
Monetization API — Phase 7: products, tracking, revenue, AI suggestions/promo.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.monetization import (
    ProductCreate,
    ProductResponse,
    PromoRequest,
    RevenueSummary,
)
from app.services.monetization_service import MonetizationService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/monetization")


def get_service(db: AsyncSession = Depends(get_db_session)) -> MonetizationService:
    return MonetizationService(db)


# ── Products ─────────────────────────────────────────────────────

@router.post("/products", response_model=ProductResponse, status_code=201,
             summary="➕ Thêm sản phẩm affiliate")
async def create_product(
    data: ProductCreate,
    service: MonetizationService = Depends(get_service),
):
    return await service.add_product(data)


@router.get("/products/{persona_id}", response_model=list[ProductResponse],
            summary="📦 Danh sách sản phẩm của persona")
async def list_products(
    persona_id: str,
    service: MonetizationService = Depends(get_service),
):
    return await service.list_products(persona_id)


# ── Tracking ─────────────────────────────────────────────────────

@router.post("/products/{product_id}/click", response_model=ProductResponse,
             summary="🖱️ Ghi nhận click affiliate")
async def record_click(
    product_id: str,
    persona_id: str = Query(...),
    source: str = Query("post"),
    service: MonetizationService = Depends(get_service),
):
    product = await service.record_click(product_id, persona_id, source)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return product


@router.post("/products/{product_id}/conversion", response_model=ProductResponse,
             summary="✅ Ghi nhận chuyển đổi (mua hàng)")
async def record_conversion(
    product_id: str,
    persona_id: str = Query(...),
    order_value: float = Query(0.0, ge=0),
    service: MonetizationService = Depends(get_service),
):
    product = await service.record_conversion(product_id, persona_id, order_value)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return product


# ── Revenue ──────────────────────────────────────────────────────

@router.get("/revenue/{persona_id}", response_model=RevenueSummary,
            summary="💰 Tổng quan doanh thu")
async def revenue(
    persona_id: str,
    service: MonetizationService = Depends(get_service),
):
    return await service.revenue_summary(persona_id)


# ── AI ───────────────────────────────────────────────────────────

@router.post("/suggest/{persona_id}", summary="🤖 AI gợi ý sản phẩm hợp ngách")
async def suggest(
    persona_id: str,
    count: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db_session),
):
    persona = await PersonaService(db).get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")
    return await MonetizationService(db).suggest_products(persona, count)


@router.post("/promo", summary="✍️ AI viết bài quảng bá sản phẩm")
async def promo(
    req: PromoRequest,
    db: AsyncSession = Depends(get_db_session),
):
    service = MonetizationService(db)
    persona = await PersonaService(db).get(req.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")
    product = await service.get_product(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return await service.generate_promo(persona, product)
